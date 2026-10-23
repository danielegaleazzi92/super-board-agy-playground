import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCart, addItem, removeItem, total } from '../src/cart.js';

test('an empty cart totals zero', () => {
  assert.equal(total(createCart()), 0);
});

test('adding the same sku twice merges the quantity', () => {
  const cart = addItem(addItem(createCart(), { sku: 'apple', price: 0.5 }), { sku: 'apple', price: 0.5, qty: 2 });
  assert.equal(cart.items.length, 1);
  assert.equal(cart.items[0].qty, 3);
  assert.equal(total(cart), 1.5);
});

test('removing a sku drops it from the total', () => {
  const cart = addItem(addItem(createCart(), { sku: 'apple', price: 0.5 }), { sku: 'bread', price: 2.2 });
  removeItem(cart, 'bread');
  assert.equal(total(cart), 0.5);
});

test('invalid items are rejected', () => {
  assert.throws(() => addItem(createCart(), { price: 1 }), /sku is required/);
  assert.throws(() => addItem(createCart(), { sku: 'x', price: -1 }), /non-negative/);
  assert.throws(() => addItem(createCart(), { sku: 'x', price: 1, qty: 0 }), /positive integer/);
});
