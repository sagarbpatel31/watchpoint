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
//
// Only measured values are sent. A reading the agent could not take — CPU on
// the first tick, temperature on hardware with no thermal zones — is omitted
// entirely rather than sent as zero, because the RCA rules cannot distinguish
// "0" from "unknown" and would read a missing sensor as a cold, idle machine.
//
// The metric names are load-bearing: apps/api/app/services/analysis.py keys its
// rules on exactly these strings, and cpu_temp_c / gpu_temp_c are what the
// thermal-throttling rule matches on.
func (c *Client) SendMetrics(m collector.SystemMetrics) error {
	timestamp := m.Timestamp.UTC().Format(time.RFC3339)
	metrics := make([]map[string]interface{}, 0, 7)

	add := func(name string, value float64, unit string) {
		metrics = append(metrics, map[string]interface{}{
			"timestamp":   timestamp,
			"metric_name": name,
			"value":       value,
			"unit":        unit,
		})
	}

	if m.CPUUsagePercent != nil {
		add("cpu_percent", *m.CPUUsagePercent, "%")
	}
	if pct, ok := m.MemoryUsedPercent(); ok {
		add("memory_percent", pct, "%")
	}
	if pct, ok := m.DiskUsedPercent(); ok {
		add("disk_used_percent", pct, "%")
	}
	if m.CPUTempC != nil {
		add("cpu_temp_c", *m.CPUTempC, "celsius")
	}
	if m.GPUTempC != nil {
		add("gpu_temp_c", *m.GPUTempC, "celsius")
	}
	if m.NetRxBytesPerSec != nil {
		add("net_rx_bytes_per_sec", *m.NetRxBytesPerSec, "bytes/s")
	}
	if m.NetTxBytesPerSec != nil {
		add("net_tx_bytes_per_sec", *m.NetTxBytesPerSec, "bytes/s")
	}

	if len(metrics) == 0 {
		return nil
	}

	return c.post("/api/v1/ingest/metrics", map[string]interface{}{"metrics": metrics})
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
