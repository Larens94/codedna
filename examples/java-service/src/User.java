package com.example.service;

// User.java — User module.
//
// exports: User | User::getId | User::getEmail | User::getName | User::isActive | User::getSuspendedAt | User::isSuspended | User::suspend | User::reactivate
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass


/**
 * User.java — Immutable user entity with suspension state management.
 *
 * exports: User(id, email, name, active, suspendedAt) | isSuspended(): boolean
 *          suspend() | reactivate() | getters
 * used_by: UserService.java → getActiveUsers, suspendUser | UserRepository.java → save
 * rules:   suspend() sets active=false atomically — never set active independently.
 *          reactivate() clears suspendedAt — both fields must change together.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */
import java.time.LocalDateTime;

public class User {

    private final int id;
    private final String email;
    private String name;
    private boolean active;
    private LocalDateTime suspendedAt;

    public User(int id, String email, String name, boolean active, LocalDateTime suspendedAt) {
        this.id = id;
        this.email = email;
        this.name = name;
        this.active = active;
        this.suspendedAt = suspendedAt;
    }

    public int getId() { return id; }
    public String getEmail() { return email; }
    public String getName() { return name; }
    public boolean isActive() { return active; }
    public LocalDateTime getSuspendedAt() { return suspendedAt; }

    public boolean isSuspended() {
        return suspendedAt != null;
    }

    public void suspend() {
        this.suspendedAt = LocalDateTime.now();
        this.active = false;
    }

    public void reactivate() {
        this.suspendedAt = null;
        this.active = true;
    }
}
