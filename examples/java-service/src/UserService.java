package com.example.service;

/**
 * UserService.java — Business logic for user lifecycle and display formatting.
 *
 * exports: getActiveUsers(): List<User> | getUserById(id): User | createUser(email, name): User
 *          suspendUser(id) | formatDisplayName(user): String
 * used_by: none
 * rules:   createUser validates email non-blank and uniqueness — throws IllegalStateException on duplicate.
 *          suspendUser delegates to User.suspend() which sets active=false atomically.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */
import java.util.List;
import java.util.stream.Collectors;

public class UserService {

    private final UserRepository repository;

    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    public List<User> getActiveUsers() {
        return repository.findAll().stream()
                .filter(u -> u.isActive() && !u.isSuspended())
                .collect(Collectors.toList());
    }

    public User getUserById(int id) {
        return repository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + id));
    }

    public User createUser(String email, String name) {
        if (email == null || email.isBlank()) {
            throw new IllegalArgumentException("email must not be blank");
        }
        if (repository.findByEmail(email).isPresent()) {
            throw new IllegalStateException("email already in use: " + email);
        }
        User user = new User(0, email, name, true, null);
        return repository.save(user);
    }

    public void suspendUser(int id) {
        User user = getUserById(id);
        user.suspend();
        repository.save(user);
    }

    public String formatDisplayName(User user) {
        String name = user.getName().trim();
        if (!name.isEmpty()) return name;
        String email = user.getEmail();
        int at = email.indexOf('@');
        return at > 0 ? email.substring(0, at) : email;
    }
}
