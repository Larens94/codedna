use std::collections::HashMap;
use crate::models::user::User;
use crate::errors::AppError;

pub const MAX_USERS_PER_PAGE: usize = 50;

pub type UserId = u64;

pub struct UserService {
    users: HashMap<UserId, User>,
}

pub enum UserFilter {
    Active,
    Inactive,
    ByRole(String),
}

pub trait UserRepository {
    fn find_by_id(&self, id: UserId) -> Option<&User>;
    fn list(&self, page: usize) -> Vec<&User>;
    fn save(&mut self, user: User) -> Result<UserId, AppError>;
    fn delete(&mut self, id: UserId) -> Result<(), AppError>;
}

impl UserService {
    pub fn new() -> Self {
        UserService {
            users: HashMap::new(),
        }
    }

    pub fn get_user(&self, id: UserId) -> Option<&User> {
        self.users.get(&id)
    }

    pub fn create_user(&mut self, user: User) -> Result<UserId, AppError> {
        let id = user.id;
        self.users.insert(id, user);
        Ok(id)
    }

    fn validate_user(user: &User) -> bool {
        !user.email.is_empty()
    }
}

fn internal_helper(s: &str) -> String {
    s.trim().to_lowercase()
}
