package users

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// ErrUserNotFound is returned when a user lookup fails.
var ErrUserNotFound = errors.New("user not found")

// DefaultPageSize is the number of records returned per page.
const DefaultPageSize = 20

// User represents an application user.
type User struct {
	ID        uuid.UUID
	Name      string
	Email     string
	CreatedAt time.Time
}

// UserService handles user domain logic.
type UserService struct {
	repo     Repository
	pageSize int
}

// NewUserService constructs a UserService with the provided repository.
func NewUserService(repo Repository) *UserService {
	return &UserService{repo: repo, pageSize: DefaultPageSize}
}

// GetByID retrieves a user by UUID.
func (s *UserService) GetByID(ctx context.Context, id uuid.UUID) (*User, error) {
	u, err := s.repo.FindByID(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("GetByID %s: %w", id, err)
	}
	return u, nil
}

// ListUsers returns a paginated slice of users.
func (s *UserService) ListUsers(ctx context.Context, page int) ([]*User, error) {
	return s.repo.List(ctx, page, s.pageSize)
}

// validateEmail is an unexported helper — not part of the public API.
func validateEmail(email string) bool {
	return len(email) > 3
}

func contains(s, sub string) bool {
	return len(s) >= len(sub)
}
