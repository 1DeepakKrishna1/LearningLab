package com.dummy.school;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Accepts a request if it carries EITHER a valid API key (X-API-Key header)
 * OR a valid JWT (Authorization: Bearer <token>). Public paths are skipped.
 */
@Component
@Order(1)
public class AuthFilter extends OncePerRequestFilter {

    private final JwtService jwt;
    private final String apiKey;
    private final boolean enabled;

    public AuthFilter(JwtService jwt,
                      @Value("${auth.api-key:my-secret-api-key}") String apiKey,
                      @Value("${auth.enabled:true}") boolean enabled) {
        this.jwt = jwt;
        this.apiKey = apiKey;
        this.enabled = enabled;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // When auth is disabled the API runs completely open.
        if (!enabled) {
            return true;
        }
        String path = request.getRequestURI();
        return "OPTIONS".equalsIgnoreCase(request.getMethod())
                || path.equals("/")
                || path.startsWith("/auth/")
                || path.startsWith("/swagger-ui")
                || path.equals("/swagger-ui.html")
                || path.startsWith("/v3/api-docs")
                || path.startsWith("/swagger-resources")
                || path.startsWith("/webjars");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        String key = request.getHeader("X-API-Key");
        if (key != null) {
            if (apiKey.equals(key)) {
                chain.doFilter(request, response);
            } else {
                unauthorized(response, "Invalid API key");
            }
            return;
        }

        String authHeader = request.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            try {
                jwt.validateAndGetSubject(authHeader.substring(7));
                chain.doFilter(request, response);
            } catch (Exception e) {
                unauthorized(response, "Invalid or expired token");
            }
            return;
        }

        unauthorized(response, "Not authenticated: provide 'X-API-Key' header or 'Authorization: Bearer <token>'");
    }

    private void unauthorized(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"" + message + "\"}");
    }
}
