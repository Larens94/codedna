// main.go — Entry point: wires HTTP mux and starts server on :8080.
//
// exports: main()
// used_by: none
// rules:   none
// agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
package main

import (
	"log"
	"net/http"

	"github.com/example/go-api/handlers"
)

func main() {
	mux := http.NewServeMux()
	handlers.RegisterRoutes(mux)
	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}
