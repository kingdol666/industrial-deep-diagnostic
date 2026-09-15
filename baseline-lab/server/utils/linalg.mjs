// Pure-JS numerical foundation — zero external dependencies.
//
// Deliberately dependency-free, matching the discipline already established by
// scripts/benchmark/baseline_pca.mjs ("pure-JS Jacobi, no venv dependency").
// Everything here is deterministic: identical input -> bit-identical output.

// ------------------------------------------------------------------ basic

export function zeros(n, m = n) {
  return Array.from({ length: n }, () => new Float64Array(m));
}

export function matmul(A, B) {
  const n = A.length, k = B.length, m = B[0].length;
  const C = zeros(n, m);
  for (let i = 0; i < n; i++) {
    const Ai = A[i], Ci = C[i];
    for (let p = 0; p < k; p++) {
      const a = Ai[p];
      if (a === 0) continue;
      const Bp = B[p];
      for (let j = 0; j < m; j++) Ci[j] += a * Bp[j];
    }
  }
  return C;
}

export function transpose(A) {
  const n = A.length, m = A[0].length;
  const T = zeros(m, n);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) T[j][i] = A[i][j];
  return T;
}

export function identity(n) {
  const I = zeros(n, n);
  for (let i = 0; i < n; i++) I[i][i] = 1;
  return I;
}

// ------------------------------------------------------- descriptive stats

export function mean(v) {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i];
  return v.length ? s / v.length : 0;
}

export function stdev(v, ddof = 1) {
  const n = v.length;
  if (n <= ddof) return 0;
  const mu = mean(v);
  let s = 0;
  for (let i = 0; i < n; i++) {
    const d = v[i] - mu;
    s += d * d;
  }
  return Math.sqrt(s / (n - ddof));
}

/** Column means/stds of a row-major matrix. */
export function colStats(X, ddof = 1) {
  const n = X.length, m = X[0].length;
  const mu = new Float64Array(m);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) mu[j] += X[i][j];
  for (let j = 0; j < m; j++) mu[j] /= n;
  const sd = new Float64Array(m);
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < m; j++) {
      const d = X[i][j] - mu[j];
      sd[j] += d * d;
    }
  }
  for (let j = 0; j < m; j++) sd[j] = Math.sqrt(sd[j] / Math.max(1, n - ddof));
  // Guard zero-variance columns (constant sensors): scale 1 keeps them inert.
  for (let j = 0; j < m; j++) if (!(sd[j] > 1e-12)) sd[j] = 1;
  return { mu, sd };
}

export function standardize(X, mu, sd) {
  const n = X.length, m = X[0].length;
  const Z = zeros(n, m);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) Z[i][j] = (X[i][j] - mu[j]) / sd[j];
  return Z;
}

/** numpy-linear quantile (matches baseline_pca.mjs exactly). */
export function quantile(sorted, q) {
  const n = sorted.length;
  if (!n) return NaN;
  if (n === 1) return sorted[0];
  const pos = (n - 1) * q;
  const lo = Math.floor(pos), hi = Math.ceil(pos);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (pos - lo) * (sorted[hi] - sorted[lo]);
}

export function pearson(a, b) {
  const n = Math.min(a.length, b.length);
  if (n < 2) return 0;
  const ma = mean(a.slice(0, n)), mb = mean(b.slice(0, n));
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    const x = a[i] - ma, y = b[i] - mb;
    num += x * y; da += x * x; db += y * y;
  }
  const den = Math.sqrt(da * db);
  return den < 1e-15 ? 0 : num / den;
}

// --------------------------------------------- symmetric eigendecomposition

/**
 * Jacobi eigenvalue decomposition for a real symmetric matrix.
 * Returns eigenvalues in DESCENDING order with matching eigenvectors
 * (eigenvectors as columns of `vectors`, i.e. A = V diag(values) V^T).
 */
export function jacobiEigen(Ain, { maxSweeps = 100, tol = 1e-12 } = {}) {
  const n = Ain.length;
  const A = Ain.map((r) => Float64Array.from(r));
  let V = identity(n);

  for (let sweep = 0; sweep < maxSweeps; sweep++) {
    let off = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += A[i][j] * A[i][j];
    if (Math.sqrt(2 * off) < tol) break;

    for (let p = 0; p < n - 1; p++) {
      for (let q = p + 1; q < n; q++) {
        const apq = A[p][q];
        if (Math.abs(apq) < 1e-300) continue;
        const theta = (A[q][q] - A[p][p]) / (2 * apq);
        const t =
          Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1);
        const s = t * c;

        for (let k = 0; k < n; k++) {
          const akp = A[k][p], akq = A[k][q];
          A[k][p] = c * akp - s * akq;
          A[k][q] = s * akp + c * akq;
        }
        for (let k = 0; k < n; k++) {
          const apk = A[p][k], aqk = A[q][k];
          A[p][k] = c * apk - s * aqk;
          A[q][k] = s * apk + c * aqk;
        }
        for (let k = 0; k < n; k++) {
          const vkp = V[k][p], vkq = V[k][q];
          V[k][p] = c * vkp - s * vkq;
          V[k][q] = s * vkp + c * vkq;
        }
      }
    }
  }

  const pairs = [];
  for (let i = 0; i < n; i++) pairs.push({ value: A[i][i], vec: V.map((row) => row[i]) });
  pairs.sort((a, b) => b.value - a.value);

  const values = Float64Array.from(pairs.map((p) => p.value));
  const vectors = zeros(n, n);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) vectors[i][j] = pairs[j].vec[i];
  return { values, vectors };
}

/** Covariance matrix of a standardized (or raw) row-major matrix. */
export function covariance(Z, ddof = 1) {
  const n = Z.length, m = Z[0].length;
  const C = zeros(m, m);
  for (let i = 0; i < n; i++) {
    const Zi = Z[i];
    for (let a = 0; a < m; a++) {
      const za = Zi[a];
      if (za === 0) continue;
      for (let b = a; b < m; b++) C[a][b] += za * Zi[b];
    }
  }
  const d = Math.max(1, n - ddof);
  for (let a = 0; a < m; a++) {
    for (let b = a; b < m; b++) {
      C[a][b] /= d;
      C[b][a] = C[a][b];
    }
  }
  return C;
}

// ------------------------------------------------ distributions (for FE T²)

/** Continued fraction for the incomplete beta function (Numerical Recipes). */
function betacf(a, b, x) {
  const MAXIT = 300, EPS = 3e-16, FPMIN = 1e-300;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1;
  let d = 1 - (qab * x) / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c;
    if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c;
    if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

function gammaln(x) {
  const cof = [
    76.18009172947146, -86.50532032941677, 24.01409824083091, -1.231739572450155,
    0.1208650973866179e-2, -0.5395239384953e-5,
  ];
  let y = x;
  const tmp0 = x + 5.5;
  const tmp = tmp0 - (x + 0.5) * Math.log(tmp0);
  let ser = 1.000000000190015;
  for (let j = 0; j < 6; j++) ser += cof[j] / ++y;
  return -tmp + Math.log((2.5066282746310005 * ser) / x);
}

/** Regularized incomplete beta I_x(a,b). */
export function betai(a, b, x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(
    gammaln(a + b) - gammaln(a) - gammaln(b) + a * Math.log(x) + b * Math.log(1 - x),
  );
  if (x < (a + 1) / (a + b + 2)) return (bt * betacf(a, b, x)) / a;
  return 1 - (bt * betacf(b, a, 1 - x)) / b;
}

/** F-distribution CDF, P(F <= x; d1, d2). scipy.stats.f.cdf. */
export function fCdf(x, d1, d2) {
  if (x <= 0) return 0;
  return betai(d1 / 2, d2 / 2, (d1 * x) / (d1 * x + d2));
}

/**
 * F-distribution inverse CDF (ppf) by bisection — replicates
 * scipy.stats.f.ppf(q, d1, d2) used by FaultExplainer's T² threshold.
 */
export function fPpf(q, d1, d2) {
  if (q <= 0) return 0;
  if (q >= 1) return Infinity;
  let lo = 0, hi = 1;
  while (fCdf(hi, d1, d2) < q && hi < 1e12) hi *= 2;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (fCdf(mid, d1, d2) < q) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

export function chi2Ppf(q, df) {
  // chi2(df) = Gamma(df/2, 2); invert via bisection on the regularized gamma.
  const cdf = (x) => (x <= 0 ? 0 : lowerGammaRegularized(df / 2, x / 2));
  let lo = 0, hi = 1;
  while (cdf(hi) < q && hi < 1e12) hi *= 2;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (cdf(mid) < q) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

/** Regularized lower incomplete gamma P(a,x) (series + continued fraction). */
export function lowerGammaRegularized(a, x) {
  if (x <= 0) return 0;
  if (x < a + 1) {
    let ap = a, sum = 1 / a, del = sum;
    for (let n = 1; n <= 500; n++) {
      ap++;
      del *= x / ap;
      sum += del;
      if (Math.abs(del) < Math.abs(sum) * 1e-16) break;
    }
    return sum * Math.exp(-x + a * Math.log(x) - gammaln(a));
  }
  // Continued fraction for Q(a,x)
  const FPMIN = 1e-300;
  let b = x + 1 - a, c = 1 / FPMIN, d = 1 / b, h = d;
  for (let i = 1; i <= 500; i++) {
    const an = -i * (i - a);
    b += 2;
    d = an * d + b;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    c = b + an / c;
    if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 1e-16) break;
  }
  return 1 - Math.exp(-x + a * Math.log(x) - gammaln(a)) * h;
}

// ------------------------------------------------------------ RNG (seeded)

/** Deterministic xorshift128 PRNG — reproducible across runs and platforms. */
export function makeRng(seed = 42) {
  let s0 = (seed >>> 0) || 1;
  let s1 = (seed * 1812433253 + 1) >>> 0 || 2;
  let s2 = (seed * 69069 + 12345) >>> 0 || 3;
  let s3 = (seed ^ 0x9e3779b9) >>> 0 || 4;
  return function next() {
    const t = (s0 ^ (s0 << 11)) >>> 0;
    s0 = s1; s1 = s2; s2 = s3;
    s3 = (s3 ^ (s3 >>> 19) ^ (t ^ (t >>> 8))) >>> 0;
    return s3 / 4294967296;
  };
}

export function shuffle(arr, rng) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
