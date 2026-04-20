// revenue.go — HTTP handlers for revenue API endpoints.
//
// exports: RegisterRoutes
// used_by: none
// rules:   month must be validated 1-12 before passing to services.
//          limit from query params capped at 100 via getLimit().
// agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/example/go-api/models"
	"github.com/example/go-api/services"
)

func RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/revenue/", revenueHandler)
}

func revenueHandler(w http.ResponseWriter, r *http.Request) {
	// placeholder routing
	users := services.GetActiveUsers()
	year := 2026
	month := 1

	if v := r.URL.Query().Get("year"); v != "" {
		year, _ = strconv.Atoi(v)
	}
	if v := r.URL.Query().Get("month"); v != "" {
		month, _ = strconv.Atoi(v)
		if month < 1 || month > 12 {
			http.Error(w, "month must be 1-12", http.StatusBadRequest)
			return
		}
	}

	data := services.MonthlyRevenue(year, month, users)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func getLimit(r *http.Request, defaultVal int) int {
	v := r.URL.Query().Get("limit")
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 1 {
		return defaultVal
	}
	if n > 100 {
		return 100
	}
	return n
}

// placeholder to satisfy import
var _ = models.User{}
