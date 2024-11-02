package com.PepsiMaxx.Smarthack.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.UUID;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/")
public class PlayController {
    @PostMapping("/session/start")
    public Mono<String> startSession(@RequestHeader(name = "API-KEY", required = true) UUID apiKey) {
        try {
            // Create the HttpClient
            HttpClient client = HttpClient.newHttpClient();

            // Build the request
            URI uri = new URI("http://localhost:8080/api/v1/session/start");
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(uri)
                    .headers("Content-Type", "text/plain;charset=UTF-8")
                    .POST(HttpRequest.BodyPublishers.ofString("7bcd6334-bc2e-4cbf-b9d4-61cb9e868869"))
                    .build();

            // Send the request and get the response
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            // Return the response body as a Mono
            return Mono.just(response.body());
        } catch (URISyntaxException e) {
            return Mono.error(new RuntimeException("Invalid URI syntax: " + e.getMessage()));
        } catch (Exception e) {
            return Mono.error(new RuntimeException("Error while sending the request: " + e.getMessage()));
        }
    }
}
