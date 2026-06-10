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
type Client struct {
	apiURL      string
	deviceID    string
	deviceName  string
	projectID   string
	deviceToken string
	httpClient  *http.Client
}

// NewClient creates a new sender client.
func NewClient(apiURL, deviceID, deviceName, projectID string) *Client {
	return &Client{
		apiURL:     apiURL,
		deviceID:   deviceID,
		deviceName: deviceName,
		projectID:  projectID,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

type registerResponse struct {
	DeviceToken string `json:"device_token"`
}

// RegisterDevice registers this device with the Watchpoint API.
func (c *Client) RegisterDevice() error {
	payload := map[string]string{
		"project_id":  c.projectID,
		"device_name": c.deviceName,
	}
	var resp registerResponse
	if err := c.postJSON("/api/v1/devices/register", payload, false, &resp); err != nil {
		return err
	}
	c.deviceToken = resp.DeviceToken
	return nil
}

// SendMetrics posts a metrics snapshot to the API as a batch.
func (c *Client) SendMetrics(m collector.SystemMetrics) error {
	now := time.Now().UTC().Format(time.RFC3339)
	metrics := []map[string]interface{}{
		{"device_id": c.deviceID, "timestamp": now, "metric_name": "cpu_percent", "value": m.CPUUsagePercent, "unit": "%"},
		{"device_id": c.deviceID, "timestamp": now, "metric_name": "memory_percent", "value": float64(m.MemoryUsedBytes) / float64(m.MemoryTotalBytes+1) * 100, "unit": "%"},
		{"device_id": c.deviceID, "timestamp": now, "metric_name": "disk_used_percent", "value": float64(m.DiskUsedBytes) / float64(m.DiskTotalBytes+1) * 100, "unit": "%"},
	}
	payload := map[string]interface{}{
		"metrics": metrics,
	}
	return c.postJSON("/api/v1/ingest/metrics", payload, true, nil)
}

// SendLog posts a log entry to the API as a batch.
func (c *Client) SendLog(level, source, message string) error {
	now := time.Now().UTC().Format(time.RFC3339)
	payload := map[string]interface{}{
		"logs": []map[string]interface{}{
			{
				"device_id": c.deviceID,
				"timestamp": now,
				"level":     level,
				"source":    source,
				"message":   message,
			},
		},
	}
	return c.postJSON("/api/v1/ingest/logs", payload, true, nil)
}

// postJSON marshals payload to JSON, POSTs it to the given path, and optionally decodes JSON.
func (c *Client) postJSON(path string, payload interface{}, auth bool, out interface{}) error {
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
	if auth && c.deviceToken != "" {
		req.Header.Set("X-Device-Token", c.deviceToken)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("send request to %s: %w", path, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("unexpected status %d from %s", resp.StatusCode, path)
	}
	if out != nil {
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			return fmt.Errorf("decode response from %s: %w", path, err)
		}
	}
	return nil
}
