import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap, catchError, throwError } from 'rxjs';
import { ConnectionStateService } from '../services/connection-state.service';

/**
 * Détecte si une erreur HTTP est un problème de connexion au backend :
 * - status 0 : navigateur n'a pas pu joindre le serveur (prod)
 * - status 502/503/504 : gateway errors
 * - status 500 + pas de body JSON : proxy Vite ECONNREFUSED (dev)
 */
function isConnectionError(error: any): boolean {
  if (error.status === 0 || error.status === 502 || error.status === 503 || error.status === 504) {
    return true;
  }
  // Vite proxy renvoie 500 avec un body texte/vide quand ECONNREFUSED
  // Une vraie erreur API 500 renvoie du JSON (error.error est un objet)
  if (error.status === 500 && !(error.error && typeof error.error === 'object')) {
    return true;
  }
  return false;
}

export const httpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const connectionState = inject(ConnectionStateService);

  return next(req).pipe(
    tap(() => {
      if (!connectionState.backendOnline()) {
        connectionState.markOnline();
      }
    }),
    catchError((error) => {
      if (isConnectionError(error)) {
        connectionState.markOffline('Connexion au backend impossible');
      }
      return throwError(() => error);
    })
  );
};
