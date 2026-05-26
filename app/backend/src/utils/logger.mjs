import winston from 'winston';
import { existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { config, PROJECT_ROOT } from '../../../../config/loader.mjs';

const cfg = config.logging || { level: 'info', format: 'json', output: 'stdout' };
const transports = [];

// Console transport
if (cfg.output === 'stdout' || cfg.output === 'both') {
  transports.push(new winston.transports.Console({
    format: cfg.format === 'json'
      ? winston.format.combine(
          winston.format.timestamp(),
          winston.format.errors({ stack: true }),
          winston.format.json(),
        )
      : winston.format.combine(
          winston.format.colorize(),
          winston.format.simple(),
        ),
  }));
}

// File transport
if (cfg.output === 'file' || cfg.output === 'both') {
  const logPath = join(PROJECT_ROOT, cfg.file_path || 'logs/app.log');
  const logDir = dirname(logPath);
  if (!existsSync(logDir)) mkdirSync(logDir, { recursive: true });
  transports.push(new winston.transports.File({
    filename: logPath,
    maxsize: (cfg.max_size_mb || 50) * 1024 * 1024,
    maxFiles: cfg.max_files || 5,
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json(),
    ),
  }));
}

// Fallback: always log to console if no transport was configured
if (transports.length === 0) {
  transports.push(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json(),
    ),
  }));
}

const logger = winston.createLogger({
  level: cfg.level || 'info',
  transports,
  exitOnError: false,
});

export function logError(context, err) {
  logger.error(`[${context}] ${err.message}`, {
    context,
    stack: err.stack,
    code: err.code,
    status: err.status,
  });
}

export default logger;
