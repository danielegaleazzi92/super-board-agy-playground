import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCart, addItem, removeItem, total, applyDiscount, clearCart } from '../src/cart.js';

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

test('applyDiscount subtracts percentage discount from total', () => {
  const cart = addItem(createCart(), { sku: 'book', price: 20 });
  applyDiscount(cart, 10);
  assert.equal(total(cart), 18);
});

test('a second applyDiscount replaces the first', () => {
  const cart = addItem(createCart(), { sku: 'book', price: 20 });
  applyDiscount(cart, 10);
  applyDiscount(cart, 25);
  assert.equal(total(cart), 15);
});

test('invalid discount percentages throw error mentioning percent', () => {
  const cart = createCart();
  assert.throws(() => applyDiscount(cart, -1), /percent/);
  assert.throws(() => applyDiscount(cart, 101), /percent/);
  assert.throws(() => applyDiscount(cart, 1.5), /percent/);
});

test('applyDiscount boundary values 0 and 100 percent work', () => {
  const cart = addItem(createCart(), { sku: 'item', price: 20 });
  applyDiscount(cart, 0);
  assert.equal(total(cart), 20);
  applyDiscount(cart, 100);
  assert.equal(total(cart), 0);
});

test('non-integer and non-number types throw error mentioning percent', () => {
  const cart = createCart();
  assert.throws(() => applyDiscount(cart, '10'), /percent/);
  assert.throws(() => applyDiscount(cart, null), /percent/);
  assert.throws(() => applyDiscount(cart, NaN), /percent/);
});

test('clearCart empties items and resets total to zero on a cart with items and discount', () => {
  const cart = addItem(addItem(createCart(), { sku: 'book', price: 10 }), { sku: 'pen', price: 5 });
  applyDiscount(cart, 10);
  clearCart(cart);
  assert.equal(cart.items.length, 0);
  assert.equal(total(cart), 0);
});

test('after clearCart, adding an item gives its full price with no surviving discount', () => {
  const cart = addItem(createCart(), { sku: 'book', price: 10 });
  applyDiscount(cart, 10);
  clearCart(cart);
  addItem(cart, { sku: 'shirt', price: 20 });
  assert.equal(total(cart), 20);
});

test('clearCart returns the same cart object so calls chain', () => {
  const cart = createCart();
  assert.equal(clearCart(cart), cart);
  const chained = addItem(clearCart(cart), { sku: 'apple', price: 0.5 });
  assert.equal(chained, cart);
  assert.equal(total(cart), 0.5);
});

test('clearCart on an empty cart is a no-op that does not throw', () => {
  const cart = createCart();
  assert.doesNotThrow(() => clearCart(cart));
  assert.equal(cart.items.length, 0);
  assert.equal(total(cart), 0);
});

test('clearCart on a cart with items but without discount empties items cleanly', () => {
  const cart = addItem(createCart(), { sku: 'hat', price: 15 });
  clearCart(cart);
  assert.equal(cart.items.length, 0);
  assert.equal(total(cart), 0);
  assert.equal('discount' in cart, false);
});
