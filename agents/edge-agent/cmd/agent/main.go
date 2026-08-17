package main

import (
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/watchpoint/edge-agent/internal/collector"
	"github.com/watchpoint/edge-agent/internal/config"
	"github.com/watchpoint/edge-agent/internal/sender"
)

func main() {
	cfg := parseFlags()

	log.Printf("Watchpoint edge-agent starting (name=%s, interval=%s, api=%s)",
		cfg.DeviceName, cfg.CollectionInterval, cfg.APIURL)

	client := sender.NewClient(cfg.APIURL, cfg.Token)

	// Device provisioning is an operator action: create the device and mint its
	// token through the API, then configure this agent with the token. The
	// agent no longer self-registers — /devices/register requires an operator
	// JWT, and self-registration is how every real device ended up in the demo
	// project.

	// Start health endpoint.
	go serveHealth()

	// The sampler is stateful: CPU usage and network rates are deltas between
	// consecutive readings of cumulative counters, so it must outlive the loop.
	// The first tick therefore reports no CPU figure.
	sampler := collector.NewSampler()

	// Run collection loop.
	ticker := time.NewTicker(cfg.CollectionInterval)
	defer ticker.Stop()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	var loggedUnsupported bool

	log.Println("Collection loop running. Press Ctrl+C to stop.")
	for {
		select {
		case <-ticker.C:
			metrics, err := sampler.Sample()
			if err != nil {
				// On a non-Linux dev machine this is permanent, so say it once
				// rather than every tick.
				if errors.Is(err, collector.ErrUnsupportedPlatform) {
					if !loggedUnsupported {
						log.Printf("No metrics collected: %v. The agent will keep "+
							"running but report nothing.", err)
						loggedUnsupported = true
					}
					continue
				}
				log.Printf("ERROR collecting metrics: %v", err)
				continue
			}

			if err := client.SendMetrics(metrics); err != nil {
				log.Printf("ERROR sending metrics: %v", err)
			} else {
				log.Printf("Metrics sent (%s)", summarize(metrics))
			}
		case sig := <-sigCh:
			log.Printf("Received %s, shutting down", sig)
			return
		}
	}
}

// summarize renders a metrics snapshot for the log line, showing "n/a" for
// readings the agent could not take rather than printing a misleading zero.
func summarize(m collector.SystemMetrics) string {
	parts := make([]string, 0, 4)

	if m.CPUUsagePercent != nil {
		parts = append(parts, fmt.Sprintf("cpu=%.1f%%", *m.CPUUsagePercent))
	} else {
		parts = append(parts, "cpu=n/a")
	}
	if pct, ok := m.MemoryUsedPercent(); ok {
		parts = append(parts, fmt.Sprintf("mem=%.1f%% of %d MB",
			pct, m.MemoryTotalBytes/(1024*1024)))
	}
	if pct, ok := m.DiskUsedPercent(); ok {
		parts = append(parts, fmt.Sprintf("disk=%.1f%%", pct))
	}
	if m.CPUTempC != nil {
		parts = append(parts, fmt.Sprintf("cpu_temp=%.1fC", *m.CPUTempC))
	}
	if m.GPUTempC != nil {
		parts = append(parts, fmt.Sprintf("gpu_temp=%.1fC", *m.GPUTempC))
	}

	return strings.Join(parts, ", ")
}

func parseFlags() config.Config {
	apiURL := flag.String("api-url", "http://localhost:8000", "Watchpoint API base URL")
	token := flag.String("token", os.Getenv("WP_DEVICE_TOKEN"),
		"Device token for ingest (default: $WP_DEVICE_TOKEN). Mint one with "+
			"POST /api/v1/devices/{device_id}/tokens")
	deviceName := flag.String("device-name", "", "Human-readable device name, used in logs only")
	interval := flag.Duration("interval", 5*time.Second, "Metrics collection interval")
	flag.Parse()

	if *token == "" {
		log.Fatal("no device token: pass -token or set WP_DEVICE_TOKEN. " +
			"Mint one with POST /api/v1/devices/{device_id}/tokens")
	}

	if *deviceName == "" {
		hostname, err := os.Hostname()
		if err != nil {
			hostname = "unknown"
		}
		*deviceName = hostname
	}

	return config.Config{
		APIURL:             *apiURL,
		Token:              *token,
		DeviceName:         *deviceName,
		CollectionInterval: *interval,
	}
}

func serveHealth() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, `{"status":"ok"}`)
	})
	log.Println("Health server listening on :8081")
	if err := http.ListenAndServe(":8081", mux); err != nil {
		log.Printf("Health server error: %v", err)
	}
}
