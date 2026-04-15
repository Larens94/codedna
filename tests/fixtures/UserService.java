package com.example.app.services;

import com.example.app.models.User;
import com.example.app.repositories.UserRepository;
import com.example.app.exceptions.UserNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.Optional;

@Service
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }

    public Optional<User> findById(Long id) {
        return userRepository.findById(id);
    }

    @Transactional
    public User create(User user) {
        validate(user);
        return userRepository.save(user);
    }

    @Transactional
    public User update(Long id, User updated) {
        User existing = userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
        existing.setName(updated.getName());
        existing.setEmail(updated.getEmail());
        return userRepository.save(existing);
    }

    @Transactional
    public void delete(Long id) {
        userRepository.deleteById(id);
    }

    private void validate(User user) {
        if (user.getEmail() == null || user.getEmail().isEmpty()) {
            throw new IllegalArgumentException("email required");
        }
    }
}
