package com.dummy.hospital;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/** Anything stored by the generic controller must carry a mutable id. */
interface Identifiable {
    Long getId();
    void setId(Long id);
}

/**
 * Generic in-memory CRUD controller.
 * Subclasses just declare the @RestController + @RequestMapping mapping.
 */
public abstract class AbstractCrudController<T extends Identifiable> {

    private final Map<Long, T> store = new ConcurrentHashMap<>();
    private final AtomicLong seq = new AtomicLong(0);

    /** Subclasses provide a human-readable name used in error messages. */
    protected abstract String entityName();

    protected T seed(T item) {
        long id = seq.incrementAndGet();
        item.setId(id);
        store.put(id, item);
        return item;
    }

    @GetMapping
    public List<T> list() {
        return List.copyOf(store.values());
    }

    @GetMapping("/{id}")
    public T get(@PathVariable Long id) {
        T item = store.get(id);
        if (item == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, entityName() + " " + id + " not found");
        }
        return item;
    }

    @PostMapping
    public ResponseEntity<T> create(@RequestBody T item) {
        long id = seq.incrementAndGet();
        item.setId(id);
        store.put(id, item);
        return ResponseEntity.status(HttpStatus.CREATED).body(item);
    }

    @DeleteMapping("/{id}")
    public Map<String, Object> delete(@PathVariable Long id) {
        if (store.remove(id) == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, entityName() + " " + id + " not found");
        }
        return Map.of("deleted", id);
    }
}
