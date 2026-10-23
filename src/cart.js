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

export function total(cart) {
  return cart.items.reduce((sum, item) => sum + item.price * item.qty, 0);
}
