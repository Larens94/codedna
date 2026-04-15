<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Services\UserService;
use App\Http\Requests\CreateUserRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class UserController extends Controller
{
    public function __construct(
        private readonly UserService $userService,
    ) {}

    public function index(Request $request): JsonResponse
    {
        $users = $this->userService->paginate($request->integer('page', 1));
        return response()->json($users);
    }

    public function show(int $id): JsonResponse
    {
        $user = $this->userService->findOrFail($id);
        return response()->json($user);
    }

    public function store(CreateUserRequest $request): JsonResponse
    {
        $user = $this->userService->create($request->validated());
        return response()->json($user, 201);
    }

    public function update(Request $request, int $id): JsonResponse
    {
        $user = $this->userService->update($id, $request->validated());
        return response()->json($user);
    }

    public function destroy(int $id): JsonResponse
    {
        $this->userService->delete($id);
        return response()->json(null, 204);
    }

    protected function authorize(string $ability, $model = null): void
    {
        parent::authorize($ability, $model);
    }

    private function resolveUser(int $id): User
    {
        return $this->userService->findOrFail($id);
    }
}
