import { useState, useEffect } from 'react';
import Telegram from '@twa-dev/sdk';

function App() {
  const [cart, setCart] = useState([]);
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [delivery, setDelivery] = useState('');
  const [payment, setPayment] = useState('');
  const [address, setAddress] = useState('');
  const userId = Telegram.initDataUnsafe.user?.id || 0;

  useEffect(() => {
    Telegram.ready();
    Telegram.expand();
    Telegram.MainButton.text = 'Кошик 🛒';
    Telegram.MainButton.show();
    Telegram.MainButton.onClick(loadCart);

    const theme = Telegram.themeParams;
    document.body.style.backgroundColor = theme.bg_color || '#f0f0f0';
    Telegram.onEvent('themeChanged', () => {
      const newTheme = Telegram.themeParams;
      document.body.style.backgroundColor = newTheme.bg_color || '#f0f0f0';
    });

    fetch('/categories')
      .then(res => res.ok ? res.json() : Promise.reject(`Error: ${res.status}`))
      .then(data => {
        setCategories(data);
        if (data.length > 0) {
          setSelectedCategory(data[0].id);
          loadProducts(data[0].id);
        }
      })
      .catch(err => {
        console.error('Fetch categories error:', err);
        Telegram.showAlert('Помилка категорій: ' + err);
      });
  }, []);

  const loadProducts = (catId) => {
    setSelectedCategory(catId);
    fetch(`/products/${catId}`)
      .then(res => res.ok ? res.json() : Promise.reject(`Error: ${res.status}`))
      .then(setProducts)
      .catch(err => {
        console.error('Fetch products error:', err);
        Telegram.showAlert('Помилка товарів: ' + err);
      });
  };

  const addToCart = (productId, name, price, photo) => {
    const newCart = [...cart];
    const existing = newCart.find(item => item.id === productId);
    if (existing) existing.quantity += 1;
    else newCart.push({ id: productId, name, price, quantity: 1, photo });
    setCart(newCart);

    fetch('/add_to_cart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, product_id: productId })
    }).catch(err => {
      console.error('Add to cart error:', err);
      Telegram.showAlert('Помилка додавання: ' + err);
    });
    Telegram.HapticFeedback.impactOccurred('medium');
    Telegram.showAlert('Додано!');
  };

  const removeFromCart = (productId) => {
    const newCart = cart.filter(item => item.id !== productId);
    setCart(newCart);

    fetch('/remove_from_cart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, product_id: productId })
    }).catch(err => {
      console.error('Remove from cart error:', err);
      Telegram.showAlert('Помилка видалення: ' + err);
    });
  };

  const loadCart = () => {
    fetch(`/cart?user_id=${userId}`)
      .then(res => res.ok ? res.json() : Promise.reject(`Error: ${res.status}`))
      .then(data => {
        setCart(data);
        setShowModal(true);
      })
      .catch(err => {
        console.error('Load cart error:', err);
        Telegram.showAlert('Помилка кошика: ' + err);
      });
  };

  const confirmOrder = () => {
    const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const products = cart.map(item => [item.id, item.quantity]);

    fetch('/create_order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, products, total, delivery, payment, address })
    })
      .then(res => res.ok ? res.json() : Promise.reject(`Error: ${res.status}`))
      .then(data => {
        setShowModal(false);
        if (payment === 'online') {
          Telegram.openInvoice({
            title: 'Оплата',
            description: 'За товари',
            payload: `order_${data.order_id}`,
            provider_token: 'YOUR_STARS_TOKEN',
            currency: 'UAH',
            prices: [{ label: 'Замовлення', amount: total * 100 }]
          }, (status) => {
            if (status === 'paid') Telegram.showAlert('Оплачено!');
          });
        } else {
          Telegram.showAlert(`Замовлення #${data.order_id} створено!`);
        }
        setCart([]);
      })
      .catch(err => {
        console.error('Confirm order error:', err);
        Telegram.showAlert('Помилка: ' + err);
      });
  };

  return (
    <div style={{ padding: '10px', paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)', display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {categories.length > 0 && (
        <div className="categories-container">
          {categories.map(cat => (
            <button
              key={cat.id}
              className={`category-btn ${selectedCategory === cat.id ? 'active' : ''}`}
              onClick={() => loadProducts(cat.id)}
              style={{ backgroundImage: cat.photo ? `url(${cat.photo})` : 'none', backgroundSize: 'cover' }}
            >
              {cat.photo ? '' : cat.name}
            </button>
          ))}
        </div>
      )}

      <div className="products-grid">
        {products.length === 0 ? (
          <p>Немає товарів в цій категорії.</p>
        ) : (
          products.map(prod => (
            <div key={prod.id} className="product-card">
              <img src={prod.photo || 'https://via.placeholder.com/150'} alt={prod.name} />
              <h3>{prod.name}</h3>
              <p>{prod.desc}</p>
              <p className="price">{prod.price} грн</p>
              <p className="stock">В наявності: {prod.stock}</p>
              <button onClick={() => addToCart(prod.id, prod.name, prod.price, prod.photo)}>Додати до кошика</button>
            </div>
          ))
        )}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <ul className="cart-items">
              {cart.length === 0 ? (
                <li>Кошик порожній.</li>
              ) : (
                cart.map(item => (
                  <li key={item.id}>
                    <span>{item.name} x{item.quantity} - {item.price * item.quantity} грн</span>
                    <button onClick={() => removeFromCart(item.id)}>Видалити</button>
                  </li>
                ))
              )}
            </ul>
            <p className="cart-total">Всього: {cart.reduce((sum, item) => sum + item.price * item.quantity, 0)} грн</p>
            <select value={delivery} onChange={e => setDelivery(e.target.value)}>
              <option value="">Оберіть доставку</option>
              <option value="Нова Пошта">Нова Пошта</option>
              <option value="Укрпошта">Укрпошта</option>
            </select>
            <select value={payment} onChange={e => setPayment(e.target.value)}>
              <option value="">Оберіть оплату</option>
              <option value="Готівкою">Готівкою</option>
              <option value="online">Онлайн</option>
            </select>
            <input value={address} onChange={e => setAddress(e.target.value)} placeholder="Адреса доставки" />
            <button className="confirm-btn" onClick={confirmOrder}>Оформити замовлення</button>
            <button className="close-btn" onClick={() => setShowModal(false)}>Закрити</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;