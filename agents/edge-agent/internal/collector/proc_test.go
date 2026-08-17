package collector

import (
	"math"
	"strings"
	"testing"
)

// Fixtures below are real text captured from a Linux host, not invented, so the
// parsers are exercised against the spacing and column layout they will meet.

const procStatFixture = `cpu  1357 0 1628 29030 125 0 22 52 0 0
cpu0 700 0 800 14500 60 0 11 26 0 0
cpu1 657 0 828 14530 65 0 11 26 0 0
intr 123456 0 0 0
ctxt 987654
`

const memInfoFixture = `MemTotal:       16461004 kB
MemFree:        15626612 kB
MemAvailable:   15871532 kB
Buffers:           28964 kB
Cached:           612340 kB
SwapTotal:             0 kB
`

const netDevFixture = `Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:    5000      50    0    0    0     0          0         0     5000      50    0    0    0     0       0          0
  eth0: 1000000    1200    0    0    0     0          0         0   250000     900    0    0    0     0       0          0
  wlan0:  500000     600    0    0    0     0          0         0   125000     450    0    0    0     0       0          0
`

func TestParseProcStat(t *testing.T) {
	st, err := parseProcStat(strings.NewReader(procStatFixture))
	if err != nil {
		t.Fatalf("parseProcStat: %v", err)
	}

	// user+nice+system+idle+iowait+irq+softirq+steal
	const wantTotal = 1357 + 0 + 1628 + 29030 + 125 + 0 + 22 + 52
	const wantIdle = 29030 + 125 // idle + iowait

	if st.total != wantTotal {
		t.Errorf("total = %d, want %d", st.total, wantTotal)
	}
	if st.idle != wantIdle {
		t.Errorf("idle = %d, want %d", st.idle, wantIdle)
	}
}

// guest and guest_nice are already counted inside user and nice. Summing them
// again would inflate total and understate busy percentage, so they must be
// dropped even when the kernel reports them.
func TestParseProcStatIgnoresGuestColumns(t *testing.T) {
	withGuest := "cpu  100 0 100 100 0 0 0 0 999999 888888\n"
	withoutGuest := "cpu  100 0 100 100 0 0 0 0\n"

	a, err := parseProcStat(strings.NewReader(withGuest))
	if err != nil {
		t.Fatalf("with guest columns: %v", err)
	}
	b, err := parseProcStat(strings.NewReader(withoutGuest))
	if err != nil {
		t.Fatalf("without guest columns: %v", err)
	}

	if a != b {
		t.Errorf("guest columns changed the result: %+v vs %+v", a, b)
	}
}

func TestParseProcStatErrors(t *testing.T) {
	tests := []struct {
		name  string
		input string
	}{
		{"no cpu line", "intr 123\nctxt 456\n"},
		{"too few fields", "cpu  100 200\n"},
		{"non-numeric field", "cpu  100 0 abc 100 0 0 0 0\n"},
		{"empty input", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if _, err := parseProcStat(strings.NewReader(tt.input)); err == nil {
				t.Error("expected an error, got nil")
			}
		})
	}
}

func TestBusyPercentSince(t *testing.T) {
	tests := []struct {
		name    string
		prev    procStat
		cur     procStat
		wantPct float64
		wantOK  bool
	}{
		{
			name:    "half the delta was busy",
			prev:    procStat{total: 1000, idle: 900},
			cur:     procStat{total: 2000, idle: 1400},
			wantPct: 50,
			wantOK:  true,
		},
		{
			name:    "fully idle",
			prev:    procStat{total: 1000, idle: 900},
			cur:     procStat{total: 2000, idle: 1900},
			wantPct: 0,
			wantOK:  true,
		},
		{
			name:    "fully busy",
			prev:    procStat{total: 1000, idle: 900},
			cur:     procStat{total: 2000, idle: 900},
			wantPct: 100,
			wantOK:  true,
		},
		{
			// The first tick, and any tick where no jiffies elapsed. Must report
			// "unknown" rather than dividing by zero or claiming 0% busy.
			name:   "no time elapsed",
			prev:   procStat{total: 1000, idle: 900},
			cur:    procStat{total: 1000, idle: 900},
			wantOK: false,
		},
		{
			// Counters can appear to regress across suspend/resume; unsigned
			// subtraction would wrap to a colossal number.
			name:   "counters went backwards",
			prev:   procStat{total: 2000, idle: 1400},
			cur:    procStat{total: 1000, idle: 900},
			wantOK: false,
		},
		{
			name:    "idle regressed but total advanced",
			prev:    procStat{total: 1000, idle: 900},
			cur:     procStat{total: 2000, idle: 800},
			wantPct: 100,
			wantOK:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := tt.cur.busyPercentSince(tt.prev)
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if ok && math.Abs(got-tt.wantPct) > 0.001 {
				t.Errorf("percent = %v, want %v", got, tt.wantPct)
			}
		})
	}
}

// The kernel's MemAvailable accounts for reclaimable page cache; MemFree does
// not. Reading MemFree by mistake reports a long-running robot as nearly out of
// memory, so this asserts the distinction directly.
func TestParseMemInfoPrefersAvailableOverFree(t *testing.T) {
	mi, err := parseMemInfo(strings.NewReader(memInfoFixture))
	if err != nil {
		t.Fatalf("parseMemInfo: %v", err)
	}

	const wantTotal = uint64(16461004) * 1024
	const wantAvail = uint64(15871532) * 1024
	const memFree = uint64(15626612) * 1024

	if mi.totalBytes != wantTotal {
		t.Errorf("totalBytes = %d, want %d", mi.totalBytes, wantTotal)
	}
	if mi.availableBytes == memFree {
		t.Fatal("availableBytes matched MemFree; parser read the wrong field")
	}
	if mi.availableBytes != wantAvail {
		t.Errorf("availableBytes = %d, want %d", mi.availableBytes, wantAvail)
	}

	pct, ok := mi.usedPercent()
	if !ok {
		t.Fatal("usedPercent not available for a valid reading")
	}
	// 16461004 - 15871532 = 589472 kB used, ~3.58%.
	if math.Abs(pct-3.58) > 0.05 {
		t.Errorf("usedPercent = %v, want about 3.58", pct)
	}
}

func TestParseMemInfoErrors(t *testing.T) {
	tests := []struct {
		name  string
		input string
	}{
		{"missing MemAvailable", "MemTotal:       16461004 kB\nMemFree: 100 kB\n"},
		{"missing MemTotal", "MemAvailable:   15871532 kB\n"},
		{"non-numeric", "MemTotal:       abc kB\nMemAvailable:   100 kB\n"},
		{"empty input", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if _, err := parseMemInfo(strings.NewReader(tt.input)); err == nil {
				t.Error("expected an error, got nil")
			}
		})
	}
}

func TestMemInfoUsedPercentZeroTotal(t *testing.T) {
	if _, ok := (memInfo{}).usedPercent(); ok {
		t.Error("usedPercent reported a value for a zero total")
	}
}

// Loopback carries the agent's own traffic to a local API. Counting it would
// show monitoring as network load on the device it is monitoring.
func TestParseNetDevExcludesLoopback(t *testing.T) {
	nc, err := parseNetDev(strings.NewReader(netDevFixture))
	if err != nil {
		t.Fatalf("parseNetDev: %v", err)
	}

	const wantRx = uint64(1000000 + 500000) // eth0 + wlan0, not lo
	const wantTx = uint64(250000 + 125000)

	if nc.rxBytes != wantRx {
		t.Errorf("rxBytes = %d, want %d (loopback must be excluded)", nc.rxBytes, wantRx)
	}
	if nc.txBytes != wantTx {
		t.Errorf("txBytes = %d, want %d (loopback must be excluded)", nc.txBytes, wantTx)
	}
}

func TestParseNetDevLoopbackOnly(t *testing.T) {
	loOnly := `Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
`
	if _, err := parseNetDev(strings.NewReader(loOnly)); err == nil {
		t.Error("expected an error when only loopback is present, got nil")
	}
}

// Reserved blocks make the raw device total a misleading denominator. These are
// the real statvfs figures from an ext4 volume with a 215 GiB reservation: df
// calls it 36% full, while used/total says 5%. The percentage must track what an
// operator can actually spend, or a disk filling up stays invisible.
func TestDiskUsedPercentMatchesDf(t *testing.T) {
	m := SystemMetrics{
		DiskTotalBytes: 270553174016, // 252.0 GiB, the whole device
		DiskUsedBytes:  14284193792,  // 13.3 GiB
		DiskFreeBytes:  25496694784,  // 23.7 GiB actually available
	}

	pct, ok := m.DiskUsedPercent()
	if !ok {
		t.Fatal("DiskUsedPercent unavailable for a valid reading")
	}
	if math.Abs(pct-35.91) > 0.05 {
		t.Errorf("DiskUsedPercent = %.2f, want about 35.91 (df's figure)", pct)
	}

	naive := float64(m.DiskUsedBytes) / float64(m.DiskTotalBytes) * 100
	if math.Abs(pct-naive) < 1 {
		t.Errorf("percentage tracked used/total (%.2f), which hides a filling disk", naive)
	}
}

// A volume with no space left must read 100%, not something comfortable.
func TestDiskUsedPercentFullVolume(t *testing.T) {
	m := SystemMetrics{
		DiskTotalBytes: 270553174016,
		DiskUsedBytes:  14284193792,
		DiskFreeBytes:  0,
	}
	pct, ok := m.DiskUsedPercent()
	if !ok {
		t.Fatal("DiskUsedPercent unavailable")
	}
	if pct != 100 {
		t.Errorf("DiskUsedPercent = %v on a volume with zero available, want 100", pct)
	}
}

func TestPercentHelpersUnavailableWhenEmpty(t *testing.T) {
	if _, ok := (SystemMetrics{}).DiskUsedPercent(); ok {
		t.Error("DiskUsedPercent reported a value with no disk reading")
	}
	if _, ok := (SystemMetrics{}).MemoryUsedPercent(); ok {
		t.Error("MemoryUsedPercent reported a value with no memory reading")
	}
}

func TestPerSecond(t *testing.T) {
	tests := []struct {
		name    string
		cur     uint64
		prev    uint64
		seconds float64
		want    float64
		wantOK  bool
	}{
		{name: "steady rate", cur: 2000, prev: 1000, seconds: 2, want: 500, wantOK: true},
		{name: "no traffic", cur: 1000, prev: 1000, seconds: 2, want: 0, wantOK: true},
		{name: "counter reset", cur: 500, prev: 1000, seconds: 2, wantOK: false},
		{name: "no time elapsed", cur: 2000, prev: 1000, seconds: 0, wantOK: false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := perSecond(tt.cur, tt.prev, tt.seconds)
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if ok && math.Abs(got-tt.want) > 0.001 {
				t.Errorf("got %v, want %v", got, tt.want)
			}
		})
	}
}

func TestClassifyThermalZone(t *testing.T) {
	tests := []struct {
		label string
		want  thermalKind
	}{
		{"GPU-therm", thermalGPU},   // Jetson
		{"CPU-therm", thermalCPU},   // Jetson
		{"gpu-thermal", thermalGPU}, // lowercase variant
		{"x86_pkg_temp", thermalCPU},
		{"coretemp", thermalCPU},
		{"acpitz", thermalCPU},
		{"soc_thermal", thermalCPU},
		{"  CPU-therm\n", thermalCPU}, // raw sysfs read keeps the newline
		{"battery", thermalOther},
		{"", thermalOther},
	}
	for _, tt := range tests {
		t.Run(tt.label, func(t *testing.T) {
			if got := classifyThermalZone(tt.label); got != tt.want {
				t.Errorf("classifyThermalZone(%q) = %v, want %v", tt.label, got, tt.want)
			}
		})
	}
}

func TestParseMilliCelsius(t *testing.T) {
	tests := []struct {
		name    string
		raw     string
		want    float64
		wantErr bool
	}{
		{name: "typical reading", raw: "45000\n", want: 45},
		{name: "no trailing newline", raw: "72500", want: 72.5},
		{name: "zero", raw: "0\n", want: 0},
		{name: "negative", raw: "-5000\n", want: -5},
		{name: "empty", raw: "\n", wantErr: true},
		{name: "non-numeric", raw: "warm\n", wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseMilliCelsius(tt.raw)
			if tt.wantErr {
				if err == nil {
					t.Error("expected an error, got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("parseMilliCelsius: %v", err)
			}
			if math.Abs(got-tt.want) > 0.001 {
				t.Errorf("got %v, want %v", got, tt.want)
			}
		})
	}
}
