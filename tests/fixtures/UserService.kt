package com.example.app.services

import com.example.app.models.User
import com.example.app.repositories.UserRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class CreateUserRequest(
    val name: String,
    val email: String,
)

class UserService(
    private val repository: UserRepository,
) {
    suspend fun findAll(): List<User> = withContext(Dispatchers.IO) {
        repository.findAll()
    }

    suspend fun findById(id: Long): User =
        repository.findById(id) ?: throw NoSuchElementException("User $id not found")

    suspend fun create(request: CreateUserRequest): User = withContext(Dispatchers.IO) {
        val user = User(name = request.name, email = request.email)
        repository.save(user)
    }

    companion object {
        fun create(repository: UserRepository): UserService = UserService(repository)
    }
}

object UserServiceDefaults {
    const val DEFAULT_PAGE_SIZE = 20
    fun defaultRepository(): UserRepository = UserRepository()
}

const val MAX_PAGE_SIZE = 100

fun formatUser(name: String, email: String): String = "$name <$email>"
