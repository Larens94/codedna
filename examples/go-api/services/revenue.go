// revenue.go — Revenue aggregation logic for monthly and annual reports.
//
// exports: GetActiveUsers() []models.User | GetInvoicesForPeriod(year, month int) []models.Invoice
//          MonthlyRevenue(year, month int, users []models.User) map[string]interface{}
//          AnnualSummary(year int, users []models.User) []map[string]interface{}
// used_by: handlers/revenue.go → revenueHandler
// rules:   GetInvoicesForPeriod returns ALL invoices, including suspended users —
//          always filter by activeIDs inside MonthlyRevenue before aggregating.
// agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
package services

import (
	"github.com/example/go-api/models"
	"github.com/example/go-api/utils"
)

// GetActiveUsers returns all non-suspended active users from the database.
func GetActiveUsers() []models.User {
	// db placeholder
	return []models.User{}
}

// GetInvoicesForPeriod returns ALL invoices for a period including suspended users.
// Callers must filter suspended users before aggregating.
func GetInvoicesForPeriod(year, month int) []models.Invoice {
	// db placeholder
	return []models.Invoice{}
}

func MonthlyRevenue(year, month int, users []models.User) map[string]interface{} {
	activeIDs := map[int]bool{}
	for _, u := range users {
		if !u.IsSuspended() {
			activeIDs[u.ID] = true
		}
	}
	invoices := GetInvoicesForPeriod(year, month)
	total := 0
	count := 0
	for _, inv := range invoices {
		if activeIDs[inv.UserID] {
			total += inv.AmountCents
			count++
		}
	}
	return map[string]interface{}{
		"year":            year,
		"month":           month,
		"total_cents":     total,
		"total_formatted": utils.FormatCurrency(total, "USD"),
		"invoice_count":   count,
	}
}

func AnnualSummary(year int, users []models.User) []map[string]interface{} {
	result := make([]map[string]interface{}, 12)
	for i := 0; i < 12; i++ {
		result[i] = MonthlyRevenue(year, i+1, users)
	}
	return result
}
