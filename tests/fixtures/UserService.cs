using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using MyApp.Data;
using MyApp.Models;

namespace MyApp.Services
{
    public class UserService : IUserService
    {
        private readonly IUserRepository _repository;
        private readonly ILogger<UserService> _logger;

        public UserService(IUserRepository repository, ILogger<UserService> logger)
        {
            _repository = repository;
            _logger = logger;
        }

        public IReadOnlyList<User> GetAll()
        {
            return _repository.GetAll();
        }

        public async Task<User> GetByIdAsync(int id)
        {
            return await _repository.FindByIdAsync(id)
                ?? throw new KeyNotFoundException($"User {id} not found");
        }

        public async Task<User> CreateAsync(CreateUserRequest request)
        {
            Validate(request);
            var user = new User { Name = request.Name, Email = request.Email };
            return await _repository.SaveAsync(user);
        }

        public async Task DeleteAsync(int id)
        {
            await _repository.DeleteAsync(id);
        }

        public int Count => _repository.Count();

        private void Validate(CreateUserRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Email))
                throw new ArgumentException("Email required");
        }
    }

    public interface IUserService
    {
        IReadOnlyList<User> GetAll();
        Task<User> GetByIdAsync(int id);
        Task<User> CreateAsync(CreateUserRequest request);
        Task DeleteAsync(int id);
    }
}
