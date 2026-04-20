# frozen_string_literal: true

# order.rb — order module.
#
# exports: Orders | Order | Order#confirm | Order#cancel | Order#amount_formatted | Order.from_hash | Order#to_json
# used_by: app.rb
# rules:   none
# agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass


require 'json'

module Orders
  class Order
    attr_accessor :user_id, :amount_cents, :status

    MAX_AMOUNT_CENTS = 10_000_000

    def initialize(user_id:, amount_cents:)
      @user_id      = user_id
      @amount_cents = amount_cents
      @status       = :pending
    end

    def confirm
      @status = :confirmed
      self
    end

    def cancel
      @status = :cancelled
      self
    end

    def amount_formatted
      format('€%.2f', @amount_cents / 100.0)
    end

    def self.from_hash(hash)
      new(user_id: hash[:user_id], amount_cents: hash[:amount_cents])
    end

    def to_json(*_args)
      { user_id: @user_id, amount_cents: @amount_cents, status: @status }.to_json
    end

    private

    def validate_amount
      raise ArgumentError, 'amount must be positive' unless @amount_cents.positive?
      raise ArgumentError, 'amount exceeds maximum'  if @amount_cents > MAX_AMOUNT_CENTS
    end
  end
end
