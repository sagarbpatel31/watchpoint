//go:build linux

package collector

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
)

// Linux telemetry sources. Stdlib only — syscall covers statfs, so the agent
// keeps its zero-dependency go.mod.
const (
	procStatPath    = "/proc/stat"
	procMemInfoPath = "/proc/meminfo"
	procNetDevPath  = "/proc/net/dev"
	thermalZoneGlob = "/sys/class/thermal/thermal_zone*"
)

// collectRaw reads one round of system telemetry.
//
// CPU, memory and disk are required: if those cannot be read the agent has
// nothing worth reporting and the error propagates. Network and temperature are
// optional — minimal containers expose only loopback, and plenty of boards have
// no thermal zones — so their absence leaves the reading unset instead of
// failing the whole sample.
func collectRaw(diskPath string) (rawSample, error) {
	var raw rawSample

	statBytes, err := os.ReadFile(procStatPath)
	if err != nil {
		return rawSample{}, fmt.Errorf("read %s: %w", procStatPath, err)
	}
	if raw.stat, err = parseProcStat(bytes.NewReader(statBytes)); err != nil {
		return rawSample{}, fmt.Errorf("parse %s: %w", procStatPath, err)
	}

	memBytes, err := os.ReadFile(procMemInfoPath)
	if err != nil {
		return rawSample{}, fmt.Errorf("read %s: %w", procMemInfoPath, err)
	}
	if raw.mem, err = parseMemInfo(bytes.NewReader(memBytes)); err != nil {
		return rawSample{}, fmt.Errorf("parse %s: %w", procMemInfoPath, err)
	}

	if raw.disk, err = readDiskUsage(diskPath); err != nil {
		return rawSample{}, err
	}

	if netBytes, err := os.ReadFile(procNetDevPath); err == nil {
		if nc, err := parseNetDev(bytes.NewReader(netBytes)); err == nil {
			raw.net, raw.haveNet = nc, true
		}
	}

	raw.cpuTempC, raw.gpuTempC = readThermalZones(thermalZoneGlob)

	return raw, nil
}

// readDiskUsage reports filesystem capacity for a mount point.
//
// Used is derived from Blocks-Bfree while free uses Bavail, matching what df
// prints: the difference is the reserved-for-root blocks, which an operator
// cannot actually spend.
func readDiskUsage(path string) (diskUsage, error) {
	var st syscall.Statfs_t
	if err := syscall.Statfs(path, &st); err != nil {
		return diskUsage{}, fmt.Errorf("statfs %s: %w", path, err)
	}

	// Bsize is int32 on 32-bit ARM and int64 elsewhere; the conversion covers
	// both of the cross-compile targets.
	blockSize := uint64(st.Bsize)
	return diskUsage{
		totalBytes: st.Blocks * blockSize,
		usedBytes:  (st.Blocks - st.Bfree) * blockSize,
		freeBytes:  st.Bavail * blockSize,
	}, nil
}

// readThermalZones returns the hottest CPU and GPU zone temperatures in degrees
// Celsius, or nil for either where no such sensor is exposed.
//
// Unreadable or unrecognised zones are skipped rather than reported: the
// thermal rule fires on these values, so a mislabelled sensor would raise a
// false incident.
func readThermalZones(glob string) (cpuTempC, gpuTempC *float64) {
	zones, err := filepath.Glob(glob)
	if err != nil {
		return nil, nil
	}

	for _, zone := range zones {
		label, err := os.ReadFile(filepath.Join(zone, "type"))
		if err != nil {
			continue
		}
		rawTemp, err := os.ReadFile(filepath.Join(zone, "temp"))
		if err != nil {
			continue
		}
		celsius, err := parseMilliCelsius(string(rawTemp))
		if err != nil {
			continue
		}

		switch classifyThermalZone(string(label)) {
		case thermalGPU:
			if gpuTempC == nil || celsius > *gpuTempC {
				v := celsius
				gpuTempC = &v
			}
		case thermalCPU:
			if cpuTempC == nil || celsius > *cpuTempC {
				v := celsius
				cpuTempC = &v
			}
		case thermalOther:
			// Unrecognised sensor (battery, ambient); not worth guessing at.
		}
	}

	return cpuTempC, gpuTempC
}
