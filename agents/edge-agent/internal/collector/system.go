package collector

import (
	"errors"
	"time"
)

// ErrUnsupportedPlatform is returned by Sample on operating systems where the
// agent cannot read real system telemetry.
//
// The agent deliberately reports nothing rather than substituting plausible
// numbers: a fabricated metric is worse than a missing one, because incident
// analysis downstream cannot tell the difference.
var ErrUnsupportedPlatform = errors.New("system metrics are only supported on Linux")

// SystemMetrics holds a snapshot of system resource usage.
//
// Fields that can legitimately be unknown are pointers and are nil when
// unmeasured — CPU and network rates need two samples to exist at all, and
// temperature sensors are absent on plenty of hardware. Callers must omit a nil
// reading rather than sending zero.
type SystemMetrics struct {
	Timestamp time.Time `json:"timestamp"`

	CPUUsagePercent *float64 `json:"cpu_usage_percent,omitempty"`

	MemoryTotalBytes     uint64 `json:"memory_total_bytes"`
	MemoryUsedBytes      uint64 `json:"memory_used_bytes"`
	MemoryAvailableBytes uint64 `json:"memory_available_bytes"`

	DiskTotalBytes uint64 `json:"disk_total_bytes"`
	DiskUsedBytes  uint64 `json:"disk_used_bytes"`
	DiskFreeBytes  uint64 `json:"disk_free_bytes"`

	NetRxBytesPerSec *float64 `json:"net_rx_bytes_per_sec,omitempty"`
	NetTxBytesPerSec *float64 `json:"net_tx_bytes_per_sec,omitempty"`

	CPUTempC *float64 `json:"cpu_temp_c,omitempty"`
	GPUTempC *float64 `json:"gpu_temp_c,omitempty"`
}

// MemoryUsedPercent reports memory in use as a percentage of total.
func (m SystemMetrics) MemoryUsedPercent() (float64, bool) {
	if m.MemoryTotalBytes == 0 {
		return 0, false
	}
	return float64(m.MemoryUsedBytes) / float64(m.MemoryTotalBytes) * 100, true
}

// DiskUsedPercent reports disk usage as a share of the space an operator can
// actually spend — used / (used + available) — which is what df prints.
//
// This deliberately does not divide by DiskTotalBytes. Filesystems reserve
// blocks that free space reports but no ordinary write can claim, and on
// quota-limited or thin-provisioned volumes the gap is enormous: a 252 GiB
// volume here exposes only 23.7 GiB as available. Dividing by the raw total
// would report that disk as 5% full when df calls it 36%, and would still read
// under 6% at the moment the last writable byte disappeared — so a disk-full
// incident would never fire.
func (m SystemMetrics) DiskUsedPercent() (float64, bool) {
	spendable := m.DiskUsedBytes + m.DiskFreeBytes
	if spendable == 0 {
		return 0, false
	}
	return float64(m.DiskUsedBytes) / float64(spendable) * 100, true
}

// diskUsage holds filesystem capacity for a single mount point.
type diskUsage struct {
	totalBytes uint64
	usedBytes  uint64
	freeBytes  uint64
}

// rawSample is one round of platform readings, before any rate maths.
type rawSample struct {
	stat procStat
	mem  memInfo
	disk diskUsage

	net     netCounters
	haveNet bool

	cpuTempC *float64
	gpuTempC *float64
}

// Sampler produces SystemMetrics snapshots.
//
// It holds state because the interesting quantities are rates: /proc/stat and
// /proc/net/dev expose counters that are cumulative since boot, so a percentage
// or a bytes-per-second needs the delta between two readings. A single reading
// cannot produce either.
type Sampler struct {
	diskPath string

	prev     procStat
	prevNet  netCounters
	prevAt   time.Time
	havePrev bool
}

// NewSampler creates a Sampler measuring disk usage at the root filesystem.
func NewSampler() *Sampler {
	return &Sampler{diskPath: "/"}
}

// Sample reads current system metrics.
//
// The first call has no previous reading to difference against, so it returns
// CPU usage and network rates as unavailable. Reporting 0% because we do not
// know yet would be indistinguishable from a genuinely idle machine.
func (s *Sampler) Sample() (SystemMetrics, error) {
	raw, err := collectRaw(s.diskPath)
	if err != nil {
		return SystemMetrics{}, err
	}
	now := time.Now().UTC()

	m := SystemMetrics{
		Timestamp:            now,
		MemoryTotalBytes:     raw.mem.totalBytes,
		MemoryUsedBytes:      raw.mem.usedBytes(),
		MemoryAvailableBytes: raw.mem.availableBytes,
		DiskTotalBytes:       raw.disk.totalBytes,
		DiskUsedBytes:        raw.disk.usedBytes,
		DiskFreeBytes:        raw.disk.freeBytes,
		CPUTempC:             raw.cpuTempC,
		GPUTempC:             raw.gpuTempC,
	}

	if s.havePrev {
		if pct, ok := raw.stat.busyPercentSince(s.prev); ok {
			m.CPUUsagePercent = &pct
		}
		elapsed := now.Sub(s.prevAt).Seconds()
		if raw.haveNet {
			if rx, ok := perSecond(raw.net.rxBytes, s.prevNet.rxBytes, elapsed); ok {
				m.NetRxBytesPerSec = &rx
			}
			if tx, ok := perSecond(raw.net.txBytes, s.prevNet.txBytes, elapsed); ok {
				m.NetTxBytesPerSec = &tx
			}
		}
	}

	s.prev = raw.stat
	s.prevAt = now
	s.havePrev = true
	if raw.haveNet {
		s.prevNet = raw.net
	}

	return m, nil
}

// perSecond converts a pair of cumulative counter readings into a rate.
//
// A counter that has gone backwards means the interface was reset or replaced;
// there is no meaningful rate to report for that interval, so the reading is
// dropped rather than clamped to zero.
func perSecond(cur, prev uint64, seconds float64) (float64, bool) {
	if seconds <= 0 || cur < prev {
		return 0, false
	}
	return float64(cur-prev) / seconds, true
}
