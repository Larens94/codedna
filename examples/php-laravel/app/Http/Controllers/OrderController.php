<?php


// OrderController.php — OrderController module.
//
// exports: OrderController | OrderController::index | OrderController::show | OrderController::store | OrderController::destroy
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

namespace App\Http\Controllers;

use App\Models\Order;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class OrderController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $orders = Order::where('user_id', $request->user()->id)
            ->orderBy('created_at', 'desc')
            ->paginate(20);

        return response()->json($orders);
    }

    public function show(string $id): JsonResponse
    {
        $order = Order::findOrFail($id);
        $this->authorize('view', $order);
        return response()->json($order);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'amount_cents' => 'required|integer|min:1|max:10000000',
        ]);

        $order = Order::create([
            'user_id'      => $request->user()->id,
            'amount_cents' => $validated['amount_cents'],
            'status'       => 'pending',
        ]);

        return response()->json($order, 201);
    }

    public function destroy(string $id): JsonResponse
    {
        $order = Order::findOrFail($id);
        $this->authorize('delete', $order);
        $order->delete();
        return response()->json(null, 204);
    }
}
