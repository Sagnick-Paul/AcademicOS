'use client';

import { useEffect } from 'react';

/**
 * Dev-only Reticle bridge component.
 *
 * Dynamically imports the SDK so none of it leaks into the production
 * bundle. Mount this once in the root layout behind a NODE_ENV guard.
 *
 * Customize `testids` and `signals` as the app grows — add every
 * data-testid value and every reticle.signal() name so the agent can
 * discover the app's testable surface automatically.
 */
export function ReticleDev() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;

    void import('@reticlehq/react').then(
      ({ reticle, install, registerCapabilities }) => {
        install();

        // Connect to the local bridge daemon.
        // For the pairing token in CI / shared environments, set
        // NEXT_PUBLIC_RETICLE_TOKEN and pass it here:
        //   reticle.connect({ token: process.env.NEXT_PUBLIC_RETICLE_TOKEN });
        reticle.connect({});

        // Declare your app's testable surface.
        // The user confirmed data-testid attributes already exist —
        // fill in the values below as you build each feature.
        registerCapabilities({
          testids: [
            // e.g. 'login-form', 'upload-btn', 'doc-list', 'nav-sidebar'
          ],
          signals: [
            // e.g. 'auth:login', 'doc:uploaded', 'doc:deleted'
          ],
          stores: [],
        });
      },
    );
  }, []);

  return null;
}
