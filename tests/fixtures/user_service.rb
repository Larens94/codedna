# frozen_string_literal: true

require_relative "models/user"
require_relative "repositories/user_repository"
require "logger"

module Services
  class UserService
    def initialize(repository = UserRepository.new)
      @repository = repository
      @logger = Logger.new($stdout)
    end

    def find_all(page: 1, per_page: 20)
      @repository.all(page: page, per_page: per_page)
    end

    def find_by_id(id)
      @repository.find(id) || raise(ArgumentError, "User #{id} not found")
    end

    def create(attrs)
      validate!(attrs)
      @repository.save(User.new(attrs))
    end

    def update(id, attrs)
      user = find_by_id(id)
      validate!(attrs)
      @repository.save(user.merge(attrs))
    end

    def self.for_tenant(tenant_id)
      new(UserRepository.scoped(tenant_id))
    end

    private

    def validate!(attrs)
      raise ArgumentError, "email required" if attrs[:email].nil?
    end

    def log_action(action, user_id)
      @logger.info("#{action}: user #{user_id}")
    end
  end
end
