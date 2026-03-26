package com.example.service;

// UserRepository.java — UserRepository module.
//
// exports: UserRepository | UserRepository::findAll | UserRepository::findById | UserRepository::findByEmail | UserRepository::save | UserRepository::deleteById
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass


/**
 * UserRepository.java — In-memory user store with CRUD operations.
 *
 * exports: findAll(): List<User> | findById(id): Optional<User>
 *          findByEmail(email): Optional<User> | save(user): User | deleteById(id)
 * used_by: UserService.java → getActiveUsers, getUserById, createUser, suspendUser
 * rules:   save() with id==0 auto-assigns a new sequential id — never pass a manually set id for new records.
 *          findByEmail is case-insensitive.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;

public class UserRepository {

    private final List<User> store = new ArrayList<>();
    private final AtomicInteger seq = new AtomicInteger(1);

    public List<User> findAll() {
        return List.copyOf(store);
    }

    public Optional<User> findById(int id) {
        return store.stream().filter(u -> u.getId() == id).findFirst();
    }

    public Optional<User> findByEmail(String email) {
        return store.stream().filter(u -> u.getEmail().equalsIgnoreCase(email)).findFirst();
    }

    public User save(User user) {
        if (user.getId() == 0) {
            User saved = new User(seq.getAndIncrement(), user.getEmail(), user.getName(),
                    user.isActive(), user.getSuspendedAt());
            store.add(saved);
            return saved;
        }
        store.removeIf(u -> u.getId() == user.getId());
        store.add(user);
        return user;
    }

    public void deleteById(int id) {
        store.removeIf(u -> u.getId() == id);
    }
}
