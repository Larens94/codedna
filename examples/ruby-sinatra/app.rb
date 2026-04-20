# frozen_string_literal: true

# app.rb — app module.
#
# exports: Orders | App
# used_by: none
# rules:   none
# agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass


require 'sinatra'
require 'json'
require_relative 'order'

module Orders
  class App < Sinatra::Base
    before { content_type :json }

    get '/orders' do
      { orders: [], total: 0 }.to_json
    end

    post '/orders' do
      data = JSON.parse(request.body.read, symbolize_names: true)
      order = Order.from_hash(data)
      status 201
      order.to_json
    end

    get '/orders/:id' do
      { id: params[:id], status: 'pending' }.to_json
    end

    delete '/orders/:id' do
      status 204
    end

    get '/health' do
      { status: 'ok' }.to_json
    end
  end
end
