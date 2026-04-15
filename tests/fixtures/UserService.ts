import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { map } from "rxjs/operators";
import { User } from "./models/user";
import { UserRepository } from "./repositories/user-repository";

export interface IUserService {
  findById(id: number): Observable<User>;
  create(data: CreateUserDto): Observable<User>;
  update(id: number, data: UpdateUserDto): Observable<User>;
  delete(id: number): Observable<void>;
}

export type CreateUserDto = {
  name: string;
  email: string;
};

export type UpdateUserDto = Partial<CreateUserDto>;

export const USER_CACHE_TTL = 300;

export class UserService implements IUserService {
  constructor(
    private readonly http: HttpClient,
    private readonly repo: UserRepository,
  ) {}

  findById(id: number): Observable<User> {
    return this.http
      .get<{ data: User }>(`/api/users/${id}`)
      .pipe(map((r) => r.data));
  }

  create(data: CreateUserDto): Observable<User> {
    return this.http.post<User>("/api/users", data);
  }

  update(id: number, data: UpdateUserDto): Observable<User> {
    return this.http.put<User>(`/api/users/${id}`, data);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/users/${id}`);
  }

  private buildUrl(path: string): string {
    return `/api${path}`;
  }
}

export class UserServiceFactory {
  static create(http: HttpClient, repo: UserRepository): UserService {
    return new UserService(http, repo);
  }
}
