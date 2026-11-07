const { app, net } = require('electron');
const { writeFileSync } = require('fs');
const out = 'D:/1010/_electron_cookie_test.json';

function withNet(url, opts = {}) {
  return new Promise((resolve, reject) => {
    const request = net.request({
      method: opts.method || 'GET',
      url,
      redirect: 'manual',
    });
    const headers = opts.headers || {};
    for (const [k, v] of Object.entries(headers)) request.setHeader(k, v);
    const chunks = [];
    request.on('response', (response) => {
      const setCookie = response.headers['set-cookie'] || [];
      response.on('data', (c) => chunks.push(Buffer.from(c)));
      response.on('end', () => {
        resolve({
          status: response.statusCode,
          headers: response.headers,
          setCookie,
          body: Buffer.concat(chunks).toString('utf8').slice(0, 200),
        });
      });
    });
    request.on('error', reject);
    request.on('redirect', (statusCode, method, redirectUrl, responseHeaders) => {
      // with redirect manual, we should get this and can abort follow
      resolve({
        status: statusCode,
        headers: responseHeaders,
        setCookie: responseHeaders['set-cookie'] || [],
        body: '',
        redirectedTo: redirectUrl,
        via: 'redirect-event',
      });
      // prevent auto follow? In electron net, need request.followRedirect() or not
      try { request.abort(); } catch (_) {}
    });
    if (opts.body) request.write(opts.body);
    request.end();
  });
}

async function withFetch(url, opts = {}) {
  const res = await fetch(url, { ...opts, redirect: 'manual' });
  let setCookie = [];
  try { setCookie = res.headers.getSetCookie ? res.headers.getSetCookie() : []; } catch (e) { setCookie = ['ERR ' + e.message]; }
  const single = res.headers.get('set-cookie');
  return {
    status: res.status,
    getSetCookie: setCookie,
    setCookieHeader: single,
    body: (await res.text()).slice(0, 120),
  };
}

app.whenReady().then(async () => {
  const result = { fetch: null, net: null };
  try {
    result.fetch = await withFetch('http://127.0.0.1:8787/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'username=admin&password=harbor-local',
    });
  } catch (e) {
    result.fetch = { error: String(e) };
  }
  try {
    result.net = await withNet('http://127.0.0.1:8787/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'username=admin&password=harbor-local',
    });
  } catch (e) {
    result.net = { error: String(e) };
  }
  writeFileSync(out, JSON.stringify(result, null, 2));
  app.quit();
});
