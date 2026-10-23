import { createCart, addItem, total } from './cart.js';

const cart = addItem(addItem(createCart(), { sku: 'apple', price: 0.5, qty: 4 }), { sku: 'bread', price: 2.2 });
console.log(`items: ${cart.items.length}, total: ${total(cart).toFixed(2)}`);
