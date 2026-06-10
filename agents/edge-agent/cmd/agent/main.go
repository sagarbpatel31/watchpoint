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

	log.Printf("Watchpoint edge-agent starting (device=%s, interval=%s, api=%s)",
		cfg.DeviceID, cfg.CollectionInterval, cfg.APIURL)

	client := sender.NewClient(cfg.APIURL, cfg.DeviceID, cfg.DeviceName, cfg.ProjectID)

	// Register device on startup.
	if err := client.RegisterDevice(); err != nil {
		log.Printf("WARNING: device registration failed: %v (will continue anyway)", err)
	} else {
		log.Println("Device registered successfully")
	}

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
	deviceID := flag.String("device-id", "", "Unique device identifier")
	deviceName := flag.String("device-name", "", "Human-readable device name")
	projectID := flag.String("project-id", "11111111-1111-1111-1111-111111111111", "Project UUID")
	interval := flag.Duration("interval", 5*time.Second, "Metrics collection interval")
	flag.Parse()

	if *deviceID == "" {
		hostname, err := os.Hostname()
		if err != nil {
			hostname = "unknown"
		}
		*deviceID = hostname
	}
	if *deviceName == "" {
		*deviceName = *deviceID
	}

	return config.Config{
		APIURL:             *apiURL,
		DeviceID:           *deviceID,
		DeviceName:         *deviceName,
		ProjectID:          *projectID,
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
