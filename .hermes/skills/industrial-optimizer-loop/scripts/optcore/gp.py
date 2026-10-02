"""gp.py — zero-new-dependency ARD-RBF Gaussian Process (numpy + scipy only).

Pinned calibration (plan §5.1 / closedloop_enums optimizer.constants):
  kernel        k(x,x') = sf^2 * exp(-0.5 * sum_i (xi-xi')^2 / li^2)
  nugget        heteroscedastic: per-point replicate s^2/n enters the diagonal
                alongside the global white-noise level sn^2
  fitting       L-BFGS-B on negative log marginal likelihood over
                theta = [log l_1..l_k, log sf, log sn], bounds [log 0.05, log 2],
                3 deterministic multi-starts
  conditioning  cond(K_y) > 1e10 -> multiply noise nugget x10, retry <= 3,
                then GPDegenerateError (strategy switches to poly_refine)
  y is standardized internally (zero mean, unit sd) so the [0.05, 2] bounds are
  scale-free; lengthscales live in coded [-1,1] units.
"""

import numpy as np
from scipy import optimize as _sps_opt

from . import (GP_BOUND_HI, GP_BOUND_LO, GP_COND_MAX, GP_N_STARTS,
               GP_NUGGET_RETRY)


class GPDegenerateError(RuntimeError):
    """K_y ill-conditioned beyond the pinned retry budget."""


def _rbf_gram(X, lengthscales, sf2):
    Z = X / lengthscales
    d2 = np.sum(Z * Z, axis=1)[:, None] + np.sum(Z * Z, axis=1)[None, :] \
        - 2.0 * Z @ Z.T
    return sf2 * np.exp(-0.5 * np.maximum(d2, 0.0))


def _cross_gram(Xa, Xb, lengthscales, sf2):
    Za, Zb = Xa / lengthscales, Xb / lengthscales
    d2 = np.sum(Za * Za, axis=1)[:, None] + np.sum(Zb * Zb, axis=1)[None, :] \
        - 2.0 * Za @ Zb.T
    return sf2 * np.exp(-0.5 * np.maximum(d2, 0.0))


class GPFit:
    """One GP per response metric; X must be coded [-1,1] (+ one-hot blocks)."""

    def __init__(self, X, y, replicate_var=None, y_raw=None):
        self.X = np.asarray(X, dtype=float)
        self.n, self.k = self.X.shape
        y = np.asarray(y, dtype=float)
        self.y_mean = float(np.mean(y)) if self.n else 0.0
        self.y_sd = float(np.std(y)) or 1.0
        self.y = (y - self.y_mean) / self.y_sd
        self.y_raw = np.asarray(y_raw, dtype=float) if y_raw is not None else y
        rv = np.zeros(self.n) if replicate_var is None \
            else np.asarray(replicate_var, dtype=float)
        self.replicate_var_std = rv / (self.y_sd ** 2)
        self.theta = None
        self.log_ml = None
        self.cond_K = None
        self.noise_level_std = None   # sn (standardized units)
        self.fallback_active = False
        self._chol = None
        self._alpha = None

    # -- kernel assembly ----------------------------------------------------
    def _split_theta(self, theta):
        ls = np.exp(np.asarray(theta[:self.k], dtype=float))
        sf2 = float(np.exp(2.0 * theta[self.k]))
        sn2 = float(np.exp(2.0 * theta[self.k + 1]))
        return ls, sf2, sn2

    def _ky(self, ls, sf2, sn2, extra_noise_mult=1.0):
        K = _rbf_gram(self.X, ls, sf2)
        diag = sn2 * extra_noise_mult + self.replicate_var_std * extra_noise_mult
        K = K + np.diag(diag + 1e-10 * sf2)
        return K

    def _neg_log_ml(self, theta, noise_mult=1.0):
        ls, sf2, sn2 = self._split_theta(theta)
        Ky = self._ky(ls, sf2, sn2, extra_noise_mult=noise_mult)
        try:
            L = np.linalg.cholesky(Ky)
        except np.linalg.LinAlgError:
            return 1e12
        a = np.linalg.solve(L.T, np.linalg.solve(L, self.y))
        logml = -0.5 * self.y @ a - np.sum(np.log(np.diag(L))) \
            - 0.5 * self.n * np.log(2.0 * np.pi)
        return -float(logml)

    # -- fitting -------------------------------------------------------------
    def fit(self):
        starts = []
        for l0 in (0.2, 0.6, 1.2)[:GP_N_STARTS]:
            theta0 = np.concatenate([
                np.full(self.k, np.log(l0)),
                [np.log(1.0), np.log(0.1)]])
            starts.append(np.clip(theta0, GP_BOUND_LO, GP_BOUND_HI))
        bounds = [(GP_BOUND_LO, GP_BOUND_HI)] * (self.k + 2)
        best = None
        for theta0 in starts:
            res = _sps_opt.minimize(self._neg_log_ml, theta0, method="L-BFGS-B",
                                    bounds=bounds)
            if best is None or res.fun < best[0]:
                best = (float(res.fun), np.asarray(res.x, dtype=float))
        noise_mult = 1.0
        for _retry in range(GP_NUGGET_RETRY + 1):
            neg_ml, theta = best
            ls, sf2, sn2 = self._split_theta(theta)
            Ky = self._ky(ls, sf2, sn2, extra_noise_mult=noise_mult)
            try:
                L = np.linalg.cholesky(Ky)
                cond = float(np.linalg.cond(Ky))
            except np.linalg.LinAlgError:
                cond = float("inf")
            if cond <= GP_COND_MAX:
                self.theta = theta
                self.log_ml = -neg_ml
                self.cond_K = cond
                self.noise_level_std = float(np.sqrt(sn2 * noise_mult))
                self._ls, self._sf2 = ls, sf2
                self._chol = L
                self._alpha = np.linalg.solve(
                    L.T, np.linalg.solve(L, self.y))
                return self
            noise_mult *= 10.0  # pinned: nugget x10 retry <= 3
        self.fallback_active = True
        raise GPDegenerateError(
            f"K_y conditioning {cond:.3g} > {GP_COND_MAX:.3g} after "
            f"{GP_NUGGET_RETRY} nugget x10 retries — degrade to poly_refine")

    # -- prediction ----------------------------------------------------------
    def predict(self, Xs, include_noise=True):
        """Returns (mu_std, sd_std) in standardized units; sd includes the
        white-noise level when include_noise (predicting observations)."""
        if self._chol is None:
            raise RuntimeError("fit() before predict()")
        Xs = np.atleast_2d(np.asarray(Xs, dtype=float))
        ks = _cross_gram(Xs, self.X, self._ls, self._sf2)
        mu = ks @ self._alpha
        v = np.linalg.solve(self._chol, ks.T)
        kss = self._sf2 * np.ones(Xs.shape[0])
        var = np.maximum(kss - np.sum(v * v, axis=0), 1e-12 * self._sf2)
        if include_noise:
            var = var + (self.noise_level_std ** 2 if self.noise_level_std else 0.0)
        return mu, np.sqrt(var)

    def predict_raw(self, Xs):
        mu, sd = self.predict(Xs)
        return mu * self.y_sd + self.y_mean, sd * self.y_sd


def ei_closed_form(mu, sigma, y_best):
    """Closed-form Expected Improvement (maximization). mu/sigma arrays."""
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    from scipy.stats import norm
    imp = mu - y_best
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(sigma > 1e-12, imp / sigma, 0.0)
        ei = imp * norm.cdf(z) + sigma * norm.pdf(z)
    return np.where(sigma > 1e-12, ei, np.maximum(imp, 0.0))


def lhs_uniform(n_samples, n_dim, seed):
    """Deterministic Latin hypercube sample on [0,1)^(n_dim)."""
    rng = np.random.default_rng(seed)
    u = np.empty((n_samples, n_dim))
    for d in range(n_dim):
        u[:, d] = (rng.permutation(n_samples) + rng.random(n_samples)) / n_samples
    return u


def mc_ei_desirability(gp_fits, X_cand, d_eval, y_best_d, seed=42,
                       n_samples=1024):
    """Desirability-MC-EI: E[max(D(y*) - D_best, 0)] with y* ~ N(mu*, sigma*)
    per metric, y* drawn via n_samples LHS inverse-normal draws (pinned
    seed=42, 1024). Decays to 0 where the model is certain nothing beats
    D_best. gp_fits: {metric: GPFit}; d_eval: fn(raw-draw matrix) -> D vec.
    Returns (ei_vector, max_ei). Deterministic.
    """
    m = len(gp_fits)
    X_cand = np.atleast_2d(np.asarray(X_cand, dtype=float))
    n_c = X_cand.shape[0]
    U = lhs_uniform(n_samples, max(m, 1), seed)
    from scipy.stats import norm as _norm
    Z = _norm.ppf(np.clip(U, 1e-9, 1 - 1e-9))          # (n_samples, m)
    draws = np.empty((n_c, n_samples, m))
    for j, metric in enumerate(gp_fits):
        mu_raw, sd_raw = gp_fits[metric].predict_raw(X_cand)
        draws[:, :, j] = mu_raw[:, None] + sd_raw[:, None] * Z[:, j][None, :]
    flat = draws.reshape(n_c * n_samples, m)
    d_flat = np.asarray(d_eval(flat), dtype=float).reshape(n_c, n_samples)
    ei = np.maximum(d_flat - float(y_best_d), 0.0).mean(axis=1)
    return ei, float(np.max(ei)) if n_c else 0.0
