<?php


// api.php — api module.
//
// exports: route:/orders | route:/orders/{id} | route:/health
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

use App\Http\Controllers\OrderController;
use Illuminate\Support\Facades\Route;

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/orders', [OrderController::class, 'index']);
    Route::post('/orders', [OrderController::class, 'store']);
    Route::get('/orders/{id}', [OrderController::class, 'show']);
    Route::delete('/orders/{id}', [OrderController::class, 'destroy']);
});

Route::get('/health', fn() => response()->json(['status' => 'ok', 'version' => '1.0']));
