// user.go — User and Invoice structs with suspension helpers.
//
// exports: User | IsSuspended | DisplayName | Invoice
// used_by: none
// rules:   always call IsSuspended() — never read SuspendedAt directly.
// agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
package models

import "time"

type User struct {
	ID          int
	Email       string
	Name        string
	IsActive    bool
	SuspendedAt *time.Time
}

func (u *User) IsSuspended() bool {
	return u.SuspendedAt != nil
}

func (u *User) DisplayName() string {
	if u.Name != "" {
		return u.Name
	}
	for i, c := range u.Email {
		if c == '@' {
			return u.Email[:i]
		}
	}
	return u.Email
}

type Invoice struct {
	ID          int
	UserID      int
	AmountCents int
	Paid        bool
	CreatedAt   time.Time
}
