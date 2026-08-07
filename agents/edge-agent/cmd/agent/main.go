package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
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

	// Run collection loop.
	ticker := time.NewTicker(cfg.CollectionInterval)
	defer ticker.Stop()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	log.Println("Collection loop running. Press Ctrl+C to stop.")
	for {
		select {
		case <-ticker.C:
			metrics := collector.Collect()
			if err := client.SendMetrics(metrics); err != nil {
				log.Printf("ERROR sending metrics: %v", err)
			} else {
				log.Printf("Metrics sent (cpu=%.1f%%, mem_used=%d MB)",
					metrics.CPUUsagePercent, metrics.MemoryUsedBytes/(1024*1024))
			}
		case sig := <-sigCh:
			log.Printf("Received %s, shutting down", sig)
			return
		}
	}
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
