// format.go — Currency, date, and string formatting utilities.
//
// exports: FormatCurrency(amountCents int, currency string) string
//          FormatDate(t time.Time) string | Truncate(s string, maxLen int) string
// used_by: services/revenue.go → MonthlyRevenue
// rules:   FormatCurrency expects integer cents, not float dollars.
// agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
package utils

import (
	"fmt"
	"time"
)

func FormatCurrency(amountCents int, currency string) string {
	symbols := map[string]string{"USD": "$", "EUR": "€", "GBP": "£"}
	symbol, ok := symbols[currency]
	if !ok {
		symbol = currency + " "
	}
	return fmt.Sprintf("%s%.2f", symbol, float64(amountCents)/100)
}

func FormatDate(t time.Time) string {
	return t.Format("2006-01-02")
}

func Truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
