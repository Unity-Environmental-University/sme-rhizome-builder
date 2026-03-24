/**
 * Preconfigured axios instance with withCredentials.
 * Replaces 30+ bare axios calls that each repeated { withCredentials: true }.
 */

import axios from 'axios';

export const api = axios.create({
  withCredentials: true,
});
