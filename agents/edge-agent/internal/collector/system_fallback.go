//go:build !linux

package collector

// collectRaw reports that real telemetry is unavailable on this platform.
//
// The agent targets Linux devices, but development happens on macOS, so the
// package must still build and run there. It returns no numbers at all: the
// previous implementation filled the gap with simulated values, which meant a
// developer running the agent locally shipped invented CPU and memory readings
// to the API indistinguishable from a real robot's. An error is the honest
// answer, and main logs it once and keeps running so local wiring work is
// unaffected.
func collectRaw(string) (rawSample, error) {
	return rawSample{}, ErrUnsupportedPlatform
}
