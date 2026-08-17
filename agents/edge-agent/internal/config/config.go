package config

import "time"

// Config holds the edge agent configuration.
type Config struct {
	APIURL string

	// Token authenticates every ingest request (X-Device-Token). The backend
	// resolves which device a batch belongs to from it, so the agent does not
	// send — or need to know — its own device UUID.
	Token string

	// DeviceName is a local label used in logs only.
	DeviceName string

	CollectionInterval time.Duration
}
