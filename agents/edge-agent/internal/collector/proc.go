package collector

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// Parsers for the Linux /proc and /sys text formats.
//
// These are deliberately pure: they take an io.Reader or a string and return
// values, doing no file I/O of their own. The platform-specific code in
// system_linux.go opens the files and hands the contents here, which keeps the
// formats testable against fixtures on any OS.

// procStat holds cumulative CPU time from the aggregate "cpu" line of
// /proc/stat, measured in jiffies since boot. A usage percentage is the delta
// between two of these, never a single reading.
type procStat struct {
	total uint64
	idle  uint64
}

// busyPercentSince returns CPU busy percentage between an earlier sample and
// this one. Counters are monotonic since boot, so a total that has not advanced
// means no time has passed and there is nothing to report.
func (s procStat) busyPercentSince(prev procStat) (float64, bool) {
	if s.total <= prev.total {
		return 0, false
	}
	totalDelta := s.total - prev.total

	// idle can appear to go backwards across a suspend/resume; clamp rather
	// than underflow the unsigned subtraction into a huge number.
	var idleDelta uint64
	if s.idle > prev.idle {
		idleDelta = s.idle - prev.idle
	}
	if idleDelta > totalDelta {
		idleDelta = totalDelta
	}

	return float64(totalDelta-idleDelta) / float64(totalDelta) * 100, true
}

// parseProcStat reads the aggregate "cpu" line from /proc/stat.
//
// Field order is: user nice system idle iowait irq softirq steal guest
// guest_nice. Only the first eight are summed — guest and guest_nice are
// already included in user and nice respectively, so counting them again
// inflates the total and depresses the reported busy percentage.
func parseProcStat(r io.Reader) (procStat, error) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		line := sc.Text()
		if !strings.HasPrefix(line, "cpu ") {
			continue
		}

		fields := strings.Fields(line)[1:]
		if len(fields) < 4 {
			return procStat{}, fmt.Errorf("cpu line has %d fields, need at least 4", len(fields))
		}
		if len(fields) > 8 {
			fields = fields[:8]
		}

		var st procStat
		for i, f := range fields {
			v, err := strconv.ParseUint(f, 10, 64)
			if err != nil {
				return procStat{}, fmt.Errorf("cpu field %d (%q): %w", i, f, err)
			}
			st.total += v
			// Fields 3 and 4 are idle and iowait; both count as not-busy.
			if i == 3 || i == 4 {
				st.idle += v
			}
		}
		return st, nil
	}
	if err := sc.Err(); err != nil {
		return procStat{}, fmt.Errorf("read /proc/stat: %w", err)
	}
	return procStat{}, errors.New("no aggregate cpu line in /proc/stat")
}

// memInfo holds system memory totals in bytes.
type memInfo struct {
	totalBytes     uint64
	availableBytes uint64
}

// usedBytes is total minus available.
func (m memInfo) usedBytes() uint64 {
	if m.availableBytes > m.totalBytes {
		return 0
	}
	return m.totalBytes - m.availableBytes
}

// usedPercent is the share of memory that is not available to new allocations.
func (m memInfo) usedPercent() (float64, bool) {
	if m.totalBytes == 0 {
		return 0, false
	}
	return float64(m.usedBytes()) / float64(m.totalBytes) * 100, true
}

// parseMemInfo reads MemTotal and MemAvailable from /proc/meminfo.
//
// MemAvailable rather than MemFree: free excludes reclaimable page cache, so on
// any long-running machine it trends towards zero and would report a healthy
// robot as out of memory. MemAvailable is the kernel's own estimate of what a
// new allocation could actually get.
func parseMemInfo(r io.Reader) (memInfo, error) {
	var mi memInfo
	var haveTotal, haveAvail bool

	sc := bufio.NewScanner(r)
	for sc.Scan() {
		key, value, found := strings.Cut(sc.Text(), ":")
		if !found {
			continue
		}
		switch key {
		case "MemTotal":
			v, err := parseMemInfoKB(value)
			if err != nil {
				return memInfo{}, fmt.Errorf("MemTotal: %w", err)
			}
			mi.totalBytes, haveTotal = v, true
		case "MemAvailable":
			v, err := parseMemInfoKB(value)
			if err != nil {
				return memInfo{}, fmt.Errorf("MemAvailable: %w", err)
			}
			mi.availableBytes, haveAvail = v, true
		}
	}
	if err := sc.Err(); err != nil {
		return memInfo{}, fmt.Errorf("read /proc/meminfo: %w", err)
	}

	if !haveTotal || !haveAvail {
		return memInfo{}, errors.New("/proc/meminfo missing MemTotal or MemAvailable")
	}
	return mi, nil
}

// parseMemInfoKB parses a "   16461004 kB" value into bytes.
func parseMemInfoKB(value string) (uint64, error) {
	fields := strings.Fields(value)
	if len(fields) == 0 {
		return 0, errors.New("empty value")
	}
	kb, err := strconv.ParseUint(fields[0], 10, 64)
	if err != nil {
		return 0, fmt.Errorf("parse %q: %w", fields[0], err)
	}
	return kb * 1024, nil
}

// netCounters holds cumulative interface byte counts since boot.
type netCounters struct {
	rxBytes uint64
	txBytes uint64
}

// parseNetDev sums receive and transmit bytes across all real interfaces in
// /proc/net/dev. Loopback is excluded: it carries the agent's own traffic to a
// local API and would otherwise show as network load caused by monitoring.
func parseNetDev(r io.Reader) (netCounters, error) {
	var nc netCounters
	var seen bool

	sc := bufio.NewScanner(r)
	for sc.Scan() {
		name, rest, found := strings.Cut(sc.Text(), ":")
		if !found {
			continue // the two header lines
		}
		if strings.TrimSpace(name) == "lo" {
			continue
		}

		// Receive bytes is the first column, transmit bytes the ninth.
		fields := strings.Fields(rest)
		if len(fields) < 9 {
			continue
		}
		rx, err := strconv.ParseUint(fields[0], 10, 64)
		if err != nil {
			return netCounters{}, fmt.Errorf("rx bytes for %q: %w", strings.TrimSpace(name), err)
		}
		tx, err := strconv.ParseUint(fields[8], 10, 64)
		if err != nil {
			return netCounters{}, fmt.Errorf("tx bytes for %q: %w", strings.TrimSpace(name), err)
		}
		nc.rxBytes += rx
		nc.txBytes += tx
		seen = true
	}
	if err := sc.Err(); err != nil {
		return netCounters{}, fmt.Errorf("read /proc/net/dev: %w", err)
	}

	if !seen {
		return netCounters{}, errors.New("no non-loopback interfaces in /proc/net/dev")
	}
	return nc, nil
}

// thermalKind classifies a thermal zone by its type label.
type thermalKind int

const (
	thermalOther thermalKind = iota
	thermalCPU
	thermalGPU
)

// classifyThermalZone maps a /sys/class/thermal/thermal_zone*/type label onto
// the metric it should feed.
//
// Jetson boards expose "CPU-therm" and "GPU-therm"; generic x86 exposes
// "x86_pkg_temp", "coretemp" or "acpitz". Anything unrecognised is ignored
// rather than guessed at — a wrong temperature is worse than none, since the
// thermal rule fires on it.
func classifyThermalZone(label string) thermalKind {
	l := strings.ToLower(strings.TrimSpace(label))
	switch {
	case strings.Contains(l, "gpu"):
		return thermalGPU
	case strings.Contains(l, "cpu"),
		strings.Contains(l, "x86_pkg_temp"),
		strings.Contains(l, "coretemp"),
		strings.Contains(l, "acpitz"),
		strings.Contains(l, "soc"):
		return thermalCPU
	default:
		return thermalOther
	}
}

// parseMilliCelsius converts a thermal zone temp reading ("45000\n") to degrees
// Celsius.
func parseMilliCelsius(raw string) (float64, error) {
	s := strings.TrimSpace(raw)
	if s == "" {
		return 0, errors.New("empty temperature reading")
	}
	milli, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("parse %q: %w", s, err)
	}
	return float64(milli) / 1000, nil
}
