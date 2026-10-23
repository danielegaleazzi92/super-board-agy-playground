// A shopping cart small enough to read in one sitting, big enough to break.

export function createCart() {
  return { items: [] };
}

export function addItem(cart, { sku, price, qty = 1 }) {
  if (!sku) throw new Error('sku is required');
  if (typeof price !== 'number' || price < 0) throw new Error('price must be a non-negative number');
  if (!Number.isInteger(qty) || qty < 1) throw new Error('qty must be a positive integer');
  const existing = cart.items.find((item) => item.sku === sku);
  if (existing) existing.qty += qty;
  else cart.items.push({ sku, price, qty });
  return cart;
}

export function removeItem(cart, sku) {
  cart.items = cart.items.filter((item) => item.sku !== sku);
  return cart;
}

export function applyDiscount(cart, percent) {
  if (!Number.isInteger(percent) || percent < 0 || percent > 100) {
    throw new Error('percent must be an integer from 0 to 100');
  }
  cart.discount = percent;
  return cart;
}

export function total(cart) {
  const subtotal = cart.items.reduce((sum, item) => sum + item.price * item.qty, 0);
  return cart.discount ? subtotal * (1 - cart.discount / 100) : subtotal;
}

export function clearCart(cart) {
  cart.items = [];
  delete cart.discount;
  return cart;
}
