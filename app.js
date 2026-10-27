const pages = ['dashboard', 'information', 'about'];
function showPage() {
  const page = location.hash.slice(1);
  const active = pages.includes(page) ? page : 'dashboard';
  document.querySelectorAll('.page').forEach(section => { section.hidden = section.id !== active; });
  document.querySelectorAll('[data-page-link]').forEach(link => {
    const selected = link.dataset.pageLink === active;
    link.classList.toggle('active', selected);
    if (selected) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', showPage);
showPage();

// --- State pilihan ---
let currentModel = 'LSTM';
let currentAsset = 'BTC';
let currentHorizon = 7;
let predictions = null;
let chart = null;
let lastBestW = null;

// Batas bobot minimum per aset (slider: 0-30%, default 20%)
let weightMinUser = 0.20;

const ASSET_NAMES = { BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana' };

// predictions.json sekarang berkunci per model: { meta, models: { LSTM: {...}, TCN: {...} } }
// Fallback ke format lama (LSTM di root) supaya dashboard tidak blank sebelum re-run script.
function modelBlock(model) {
  if (!predictions) return null;
  if (predictions.models) return predictions.models[model] || null;
  return model === 'LSTM' ? predictions : null;
}
function analysisBlock(model, horizon) {
  return modelBlock(model)?.analysis?.[String(horizon)] || null;
}

document.querySelectorAll('[data-model]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-model]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  currentModel = button.dataset.model;
  document.querySelectorAll('[data-model-name]').forEach(item => { item.textContent = currentModel; });
  renderChart();
  renderAnalysis();
  renderBacktest();
  renderWeights();
}));
document.querySelectorAll('[data-asset]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-asset]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  currentAsset = button.dataset.asset;
  document.querySelectorAll('[data-asset-name]').forEach(item => { item.textContent = button.dataset.name; });
  renderChart();
  renderAnalysis();
  renderBacktest();
}));
document.querySelectorAll('[data-days]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-days]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  currentHorizon = Number(button.dataset.days);
  document.querySelectorAll('[data-horizon]').forEach(item => { item.textContent = button.dataset.days; });
  renderAnalysis();
  renderBacktest();
  renderWeights();
}));

// --- Slider bobot minimum per aset + tombol konfirmasi ---
const minSlider = document.getElementById('min-weight-slider');
const minSliderVal = document.getElementById('min-weight-val');
const minConfirm = document.getElementById('min-weight-confirm');
if (minSlider) {
  minSlider.addEventListener('input', () => {
    minSliderVal.textContent = minSlider.value + '%';
  });
}
if (minConfirm) {
  minConfirm.addEventListener('click', () => {
    weightMinUser = Number(minSlider.value) / 100;
    renderWeights();
  });
}

// --- Simulasi Modal ---
let simModal = null;
const simModalInput = document.getElementById('sim-modal');
const simCalc = document.getElementById('sim-calc');
if (simCalc) {
  simCalc.addEventListener('click', () => {
    simModal = Number(simModalInput.value) || 0;
    renderSimulation(lastBestW);
  });
}

const disclaimer = document.getElementById('disclaimer-dialog');
document.getElementById('disclaimer-open').addEventListener('click', () => disclaimer.showModal());
disclaimer.addEventListener('click', event => { if (event.target === disclaimer) disclaimer.close(); });

// --- Chart: historis 60d + forecast 1/3/7/14/30 (seperti plot_historical_vs_points) ---
function setStatus(msg) {
  document.getElementById('chart-status').textContent = msg;
}

async function loadPredictions() {
  try {
    const res = await fetch('predictions.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    predictions = await res.json();
    const available = predictions.models ? Object.keys(predictions.models) : ['LSTM'];
    setStatus('predictions.json (' + available.join(', ') + ') · ' + (predictions.meta?.generated_at || 'tanpa tanggal') + '.');
  } catch (e) {
    predictions = null;
    setStatus(
      'predictions.json belum ditemukan. Jalankan: py -3.12 generate_predictions.py, lalu buka via http:// (Live Server / npx serve). Detail: F12 > Console. [' + e.message + ']'
    );
    console.warn('Gagal load predictions.json:', e);
  }
  renderChart();
  renderAnalysis();
  renderBacktest();
  renderWeights();
}

function renderChart() {
  const canvas = document.getElementById('pred-chart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (chart) { chart.destroy(); chart = null; }

  // Model tanpa file .keras-nya -> kosongkan panel (status menjelaskan alasannya)
  const block = modelBlock(currentModel);
  if (!block) {
    setStatus('Model ' + currentModel + ' belum tersedia di predictions.json. Jalankan ulang py -3.12 generate_predictions.py setelah training model tersebut.');
    return;
  }
  const entry = block[currentAsset];
  if (!entry) return;

  const hDates = entry.history.dates;
  const hClose = entry.history.close;
  const lastDate = entry.last_date;
  const lastClose = entry.last_close;
  const hs = Object.keys(entry.forecast).map(Number).sort((a, b) => a - b);

  // Dataset 1: garis historis (60 titik). Dataset 2: garis forecast (titik sambung last + 5 titik h).
  const forecastDates = [lastDate, ...hs.map(h => entry.forecast[String(h)].date)];
  const forecastPrices = [lastClose, ...hs.map(h => entry.forecast[String(h)].price)];

  // Samakan sumbu-x: gabung tanggal historis + tanggal forecast (tanpa duplikat last_date bila sama).
  const labels = [...hDates];
  hs.forEach(h => {
    const d = entry.forecast[String(h)].date;
    if (!labels.includes(d)) labels.push(d);
  });
  const histAligned = labels.map(d => {
    const i = hDates.indexOf(d);
    return i >= 0 ? hClose[i] : null;
  });
  const fcAligned = labels.map(d => {
    const i = forecastDates.indexOf(d);
    return i >= 0 ? forecastPrices[i] : null;
  });

  setStatus(
    currentModel + ' · ' + currentAsset + ' · harga terakhir Rp' + Math.round(lastClose).toLocaleString('id-ID') +
    ' (' + lastDate + ') · forecast: ' + hs.map(h => 'H+' + h + ' Rp' + Math.round(entry.forecast[String(h)].price).toLocaleString('id-ID')).join(' | ')
  );

  chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Actual (60 hari)', data: histAligned, borderColor: '#7fb3ff', tension: 0.2, pointRadius: 0 },
        { label: 'Predicted ' + currentModel + ' (1/3/7/14/30)', data: fcAligned, borderColor: '#7dff9b', borderDash: [6, 4], tension: 0.2, pointRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: '#aaa' }, grid: { color: '#333' } },
        y: { ticks: { color: '#aaa' }, grid: { color: '#333' } }
      },
      plugins: { legend: { labels: { color: '#eee' } } }
    }
  });
}

// --- Tabel expected return & risiko per aset (mirror sel Markowitz notebook) ---
function renderAnalysis() {
  const body = document.getElementById('returns-body');
  const status = document.getElementById('returns-status');
  const hLabel = document.getElementById('returns-horizon-label');
  if (!body) return;
  if (hLabel) hLabel.textContent = '· ' + currentHorizon + ' hari';

  const block = analysisBlock(currentModel, currentHorizon);
  if (!block) {
    body.innerHTML = '';
    return;
  }
  const order = ['BTC', 'ETH', 'SOL'].filter(a => block.assets[a]);
  body.innerHTML = order.map(a => {
    const r = block.assets[a];
    const er = (r.expected_return * 100).toFixed(2) + '%';
    const risk = (r.risk * 100).toFixed(2) + '%';
    const erCls = r.expected_return >= 0 ? 'pos' : 'neg';
    return '<tr><td><strong>' + a + '</strong> <span class="muted">' + (ASSET_NAMES[a] || '') + '</span></td>' +
      '<td>Rp' + Math.round(r.last).toLocaleString('id-ID') + '</td>' +
      '<td class="muted">' + (r.date || '-') + '</td>' +
      '<td>Rp' + Math.round(r.pred).toLocaleString('id-ID') + '</td>' +
      '<td class="' + erCls + '">' + er + '</td><td>' + risk + '</td></tr>';
  }).join('');
  if (status) status.textContent = currentModel + ' · μ = (prediksi − terakhir) / terakhir · σ dari covariance 90 hari × ' + currentHorizon + ' hari · update: ' + (predictions.meta?.generated_at || '-');
}

// --- Backtesting metrics per horizon (update saat horizon diganti) ---
function renderBacktest() {
  const grid = document.getElementById('metrics-grid');
  const hLabel = document.getElementById('backtest-horizon-label');
  const status = document.getElementById('backtest-status');
  if (!grid) return;
  if (hLabel) hLabel.textContent = '· ' + currentHorizon + ' hari';

  const bt = predictions?.backtest?.[currentModel]?.[String(currentHorizon)]?.[currentAsset];
  if (!bt) {
    grid.innerHTML = '<p class="muted-cell" style="grid-column: 1 / -1;">Menunggu predictions.json (dengan backtest h=' + currentHorizon + ')…</p>';
    return;
  }

  const mae = 'Rp' + Math.round(bt.MAE).toLocaleString('id-ID');
  const rmse = 'Rp' + Math.round(bt.RMSE).toLocaleString('id-ID');
  const mape = bt.MAPE.toFixed(2) + '%';
  const r2 = bt.R2.toFixed(4);

  grid.innerHTML =
    '<div class="metric-card"><span class="metric-label">MAE</span><span class="metric-value">' + mae + '</span></div>' +
    '<div class="metric-card"><span class="metric-label">RMSE</span><span class="metric-value">' + rmse + '</span></div>' +
    '<div class="metric-card"><span class="metric-label">MAPE</span><span class="metric-value">' + mape + '</span></div>' +
    '<div class="metric-card"><span class="metric-label">R²</span><span class="metric-value">' + r2 + '</span></div>';

  if (status) status.textContent = currentModel + ' · MAE / RMSE dalam Rupiah · MAPE dalam % · R² mendekati 1 = lebih baik · update: ' + (predictions.meta?.generated_at || '-');
}

// --- Simulasi Modal ---
function renderSimulation(bestW) {
  const result = document.getElementById('sim-result');
  const body = document.getElementById('sim-body');
  const modalTotal = document.getElementById('sim-modal-total');
  const portfolioTotal = document.getElementById('sim-portfolio-total');
  const plTotal = document.getElementById('sim-pl-total');
  if (!result || !body) return;

  if (!simModal || simModal <= 0) {
    result.style.display = 'none';
    return;
  }

  const block = analysisBlock(currentModel, 7);
  if (!block || !block.portfolio) {
    result.style.display = 'none';
    return;
  }
  const pf = block.portfolio;

  // Gunakan bestW (dari slider) jika tersedia, jika tidak gunakan portfolio dari JSON
  const weightsFromSlider = bestW;
  const order = weightsFromSlider ? ['BTC', 'ETH', 'SOL'] : Object.keys(block.assets).filter(a => block.assets[a]);
  if (order.length === 0) {
    result.style.display = 'none';
    return;
  }

  let totalPredValue = 0;
  let rows = '';

  order.forEach((a, i) => {
    const r = block.assets[a];
    if (!r) return;
    const weight = weightsFromSlider ? weightsFromSlider[i] : pf.weights[a];
    const alloc = simModal * weight;
    const units = alloc / r.last;
    const predValue = units * r.pred;
    totalPredValue += predValue;
    const pl = predValue - alloc;
    const plCls = pl >= 0 ? 'pos' : 'neg';
    rows += '<tr><td><strong>' + a + '</strong> <span class="muted">' + (ASSET_NAMES[a] || '') + '</span></td>' +
      '<td>' + (weight * 100).toFixed(1) + '%</td>' +
      '<td>' + units.toFixed(6) + '</td>' +
      '<td>Rp' + Math.round(predValue).toLocaleString('id-ID') + '</td>' +
      '<td class="' + plCls + '">' + (pl >= 0 ? '+' : '') + 'Rp' + Math.round(pl).toLocaleString('id-ID') + '</td></tr>';
  });

  const totalPL = totalPredValue - simModal;
  const plCls = totalPL >= 0 ? 'pos' : 'neg';

  body.innerHTML = rows;
  modalTotal.textContent = 'Rp' + Math.round(simModal).toLocaleString('id-ID');
  portfolioTotal.textContent = 'Rp' + Math.round(totalPredValue).toLocaleString('id-ID');
  plTotal.innerHTML = 'Keuntungan / Kerugian: <strong class="' + plCls + '">' + (totalPL >= 0 ? '+' : '') + 'Rp' + Math.round(totalPL).toLocaleString('id-ID') + '</strong>';
  result.style.display = 'block';
}

// --- Bobot portofolio Markowitz, horizon TETAP 7 hari (mingguan) ---
// Alasan: crypto volatil — horizon 1/3 hari memaksa rebalancing terlalu sering
// (biaya transaksi menumpuk), 14/30 hari terlalu lama (kalah momentum).
function renderWeights() {
  const body = document.getElementById('weights-body');
  const status = document.getElementById('weights-status');
  if (!body) return;

  const block = analysisBlock(currentModel, 7);
  if (!block) {
    body.innerHTML = '';
    if (status) status.textContent = 'Menunggu predictions.json…';
    return;
  }

  const mu = block.mu || [];
  const cov = block.cov || [];
  const rf = block.rf || 0;

  if (!mu.length || !cov.length) {
    body.innerHTML = '';
    return;
  }

  const min = weightMinUser;
  // Maksimum dinamis: sisa alokasi setelah minimum dipenuhi dua aset lain
  // Contoh: min 26% → max 48%; min 30% → max 40% (memungkinkan 30/30/40)
  const max = 1 - 2 * min;

  // Validasi dasar: min harus <= 1/3 agar feasible
  if (min > 1/3 + 1e-9) {
    body.innerHTML = '<p class="muted-cell" style="color:#ff9b9b;">Batas tidak valid: minimum terlalu besar.</p>';
    if (status) status.textContent = 'Batas bobot tidak feasible.';
    return;
  }

  // Grid search Sharpe Ratio
  let bestSharpe = -Infinity;
  let bestW = [1/3, 1/3, 1/3];
  const step = 0.01;

  for (let w0 = min; w0 <= max + 1e-9; w0 += step) {
    for (let w1 = min; w1 <= max + 1e-9; w1 += step) {
      let w2 = 1 - w0 - w1;
      if (w2 < min - 1e-9 || w2 > max + 1e-9) continue;

      const weights = [w0, w1, w2];
      // portofolio return
      let portRet = 0;
      for (let i = 0; i < 3; i++) portRet += weights[i] * mu[i];

      // portofolio variansi
      let portVar = 0;
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
          portVar += weights[i] * cov[i][j] * weights[j];
        }
      }
      const portStd = Math.sqrt(Math.max(0, portVar));
      const sharpe = portStd === 0 ? 0 : (portRet - rf) / portStd;

      if (sharpe > bestSharpe) {
        bestSharpe = sharpe;
        bestW = [w0, w1, w2];
      }
    }
  }

  const order = ['BTC', 'ETH', 'SOL'];
  const w = bestW;
  const portRet = w[0]*mu[0] + w[1]*mu[1] + w[2]*mu[2];
  const portVar = w[0]*w[0]*cov[0][0] + w[1]*w[1]*cov[1][1] + w[2]*w[2]*cov[2][2]
    + 2*w[0]*w[1]*cov[0][1] + 2*w[0]*w[2]*cov[0][2] + 2*w[1]*w[2]*cov[1][2];
  const portStd = Math.sqrt(Math.max(0, portVar));

  body.innerHTML =
    order.map((a, i) => {
      const pct = w[i] * 100;
      return '<div class="weight-row"><span class="w-name">' + a + ' <span class="muted">' + (ASSET_NAMES[a] || '') + '</span></span>' +
        '<span class="weight-track"><span class="weight-fill" style="display:block;width:' + pct.toFixed(1) + '%"></span></span>' +
        '<span class="weight-pct">' + pct.toFixed(1) + '%</span></div>';
    }).join('') +
    '<div class="weight-stats"><span>Expected return <strong>' + (portRet * 100).toFixed(2) + '%</strong></span>' +
    '<span>Risiko <strong>' + (portStd * 100).toFixed(2) + '%</strong></span>' +
    '<span>Sharpe <strong>' + bestSharpe.toFixed(3) + '</strong></span></div>';

  if (status) status.textContent = currentModel + ' · horizon 7 hari · min. bobot ' + (min*100).toFixed(0) + '%/aset · update: ' + (predictions.meta?.generated_at || '-');

  lastBestW = bestW;
  renderSimulation(bestW);
}

loadPredictions();
