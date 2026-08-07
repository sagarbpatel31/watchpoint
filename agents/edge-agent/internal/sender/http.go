package sender

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/watchpoint/edge-agent/internal/collector"
)

// Client sends telemetry data to the Watchpoint API.
//
// Authentication is a device token in the X-Device-Token header. The backend
// attributes each batch to the device that owns the token, so no device_id is
// sent: the agent has no reliable way to know its own UUID, and previously sent
// its hostname, which the API rejected as a malformed UUID.
type Client struct {
	apiURL     string
	token      string
	httpClient *http.Client
}

// NewClient creates a new sender client.
func NewClient(apiURL, token string) *Client {
	return &Client{
		apiURL: apiURL,
		token:  token,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// SendMetrics posts a metrics snapshot to the API as a batch.
func (c *Client) SendMetrics(m collector.SystemMetrics) error {
	now := time.Now().UTC().Format(time.RFC3339)
	metrics := []map[string]interface{}{
		{"timestamp": now, "metric_name": "cpu_percent", "value": m.CPUUsagePercent, "unit": "%"},
		{"timestamp": now, "metric_name": "memory_percent", "value": float64(m.MemoryUsedBytes) / float64(m.MemoryTotalBytes+1) * 100, "unit": "%"},
		{"timestamp": now, "metric_name": "disk_used_percent", "value": float64(m.DiskUsedBytes) / float64(m.DiskTotalBytes+1) * 100, "unit": "%"},
	}
	payload := map[string]interface{}{
		"metrics": metrics,
	}
	return c.post("/api/v1/ingest/metrics", payload)
}

// SendLog posts a log entry to the API as a batch.
func (c *Client) SendLog(level, source, message string) error {
	now := time.Now().UTC().Format(time.RFC3339)
	payload := map[string]interface{}{
		"logs": []map[string]interface{}{
			{
				"timestamp": now,
				"level":     level,
				"source":    source,
				"message":   message,
			},
		},
	}
	return c.post("/api/v1/ingest/logs", payload)
}

// post marshals payload to JSON and POSTs it to the given path.
func (c *Client) post(path string, payload interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	url := c.apiURL + path
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Device-Token", c.token)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("send request to %s: %w", path, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("unexpected status %d from %s", resp.StatusCode, path)
	}
	return nil
}
