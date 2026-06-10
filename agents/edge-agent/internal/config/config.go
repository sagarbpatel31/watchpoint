package config

import "time"

// Config holds the edge agent configuration.
type Config struct {
	APIURL             string
	DeviceID           string
	DeviceName         string
	ProjectID          string
	CollectionInterval time.Duration
}
