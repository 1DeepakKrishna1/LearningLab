package com.dummy.school;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeIn;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeType;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.security.SecurityScheme;
import io.swagger.v3.oas.annotations.security.SecuritySchemes;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * School Dummy REST API.
 *
 * Entities: students, teachers, courses, classrooms, enrollments.
 * Each entity exposes GET (list), GET /{id}, POST and DELETE /{id}.
 *
 * Swagger UI : http://localhost:<PORT>/swagger-ui.html
 * OpenAPI    : http://localhost:<PORT>/v3/api-docs
 *
 * Port is configured in application.properties (default 8081) and can be
 * overridden with --server.port=XXXX or the SERVER_PORT environment variable.
 */
@SpringBootApplication
@OpenAPIDefinition(
        info = @Info(title = "School API", version = "1.0.0",
                description = "Dummy school REST API with students, teachers, courses, classrooms and enrollments. "
                        + "Authenticate with an API key (X-API-Key) or a JWT from POST /auth/login (admin/password)."),
        security = {@SecurityRequirement(name = "ApiKeyAuth"), @SecurityRequirement(name = "BearerAuth")})
@SecuritySchemes({
        @SecurityScheme(name = "ApiKeyAuth", type = SecuritySchemeType.APIKEY,
                in = SecuritySchemeIn.HEADER, paramName = "X-API-Key"),
        @SecurityScheme(name = "BearerAuth", type = SecuritySchemeType.HTTP,
                scheme = "bearer", bearerFormat = "JWT")
})
public class SchoolApplication {
    public static void main(String[] args) {
        SpringApplication.run(SchoolApplication.class, args);
    }
}
