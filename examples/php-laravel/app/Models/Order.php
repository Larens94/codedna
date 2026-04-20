<?php


// Order.php — Order module.
//
// exports: Order | Order::user(): BelongsTo | Order::isActive(): bool | Order::amountFormatted(): string
// used_by: app/Http/Controllers/OrderController.php
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Order extends Model
{
    use HasFactory;

    protected $fillable = ['user_id', 'amount_cents', 'status', 'created_at'];

    protected $casts = [
        'amount_cents' => 'integer',
        'created_at'   => 'datetime',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function isActive(): bool
    {
        return $this->status === 'active';
    }

    public function amountFormatted(): string
    {
        return '€' . number_format($this->amount_cents / 100, 2);
    }
}
