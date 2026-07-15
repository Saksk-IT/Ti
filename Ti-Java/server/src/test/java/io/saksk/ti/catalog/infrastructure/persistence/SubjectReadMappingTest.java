package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.domain.SubjectSnapshot;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.hibernate.annotations.Immutable;
import org.junit.jupiter.api.Test;
import org.springframework.data.repository.CrudRepository;
import org.springframework.data.repository.Repository;
import org.springframework.transaction.annotation.Transactional;

class SubjectReadMappingTest {

    @Test
    void mapsTheNineCurrentLegacyColumnsWithoutJpaRelationshipsOrWriteableColumns() {
        assertThat(SubjectReadEntity.class)
                .hasAnnotation(Entity.class)
                .hasAnnotation(Immutable.class);
        assertThat(SubjectReadEntity.class.getAnnotation(Table.class).name()).isEqualTo("subjects");

        Map<String, ColumnShape> expected = new LinkedHashMap<>();
        expected.put("id", new ColumnShape(Integer.class, false));
        expected.put("name", new ColumnShape(String.class, false));
        expected.put("description", new ColumnShape(String.class, true));
        expected.put("is_locked", new ColumnShape(Boolean.class, true));
        expected.put("plaza_board_id", new ColumnShape(Integer.class, true));
        expected.put("is_plaza_featured", new ColumnShape(boolean.class, false));
        expected.put("plaza_featured_weight", new ColumnShape(int.class, false));
        expected.put("plaza_featured_at", new ColumnShape(LocalDateTime.class, true));
        expected.put("created_at", new ColumnShape(LocalDateTime.class, true));

        Map<String, ColumnShape> actual = Arrays.stream(SubjectReadEntity.class.getDeclaredFields())
                .filter(field -> field.isAnnotationPresent(Column.class))
                .collect(Collectors.toMap(
                        field -> field.getAnnotation(Column.class).name(),
                        field -> new ColumnShape(field.getType(), field.getAnnotation(Column.class).nullable()),
                        (left, right) -> {
                            throw new AssertionError("duplicate column mapping: " + left);
                        },
                        LinkedHashMap::new));

        assertThat(actual).containsExactlyInAnyOrderEntriesOf(expected);
        assertThat(Arrays.stream(SubjectReadEntity.class.getDeclaredFields())
                        .filter(field -> field.isAnnotationPresent(Column.class)))
                .allSatisfy(field -> {
                    Column column = field.getAnnotation(Column.class);
                    assertThat(column.insertable()).as("%s insertable", column.name()).isFalse();
                    assertThat(column.updatable()).as("%s updatable", column.name()).isFalse();
                });
        assertThat(idFields()).containsExactly("id");
        assertThat(Arrays.stream(SubjectReadEntity.class.getDeclaredFields()))
                .noneMatch(SubjectReadMappingTest::hasJpaRelationship);
    }

    @Test
    void repositorySurfaceExposesOnlyReadOperations() {
        assertThat(Repository.class).isAssignableFrom(SubjectReadRepository.class);
        assertThat(CrudRepository.class.isAssignableFrom(SubjectReadRepository.class)).isFalse();
        assertThat(Arrays.stream(SubjectReadRepository.class.getMethods()).map(Method::getName))
                .containsExactlyInAnyOrder("findById", "findAllByOrderByNameAsc")
                .noneMatch(name -> name.startsWith("save") || name.startsWith("delete"));

        Transactional transaction = SubjectReadRepository.class.getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.readOnly()).isTrue();
    }

    @Test
    void entityHydrationPreservesNullableLegacyValuesAndScalarForeignId() {
        LocalDateTime featuredAt = LocalDateTime.of(2026, 7, 16, 9, 30);
        LocalDateTime createdAt = LocalDateTime.of(2026, 2, 25, 1, 5);
        SubjectReadEntity entity = new SubjectReadEntity(
                7, "数据结构", null, null, 12, true, 30, featuredAt, createdAt);

        SubjectSnapshot snapshot = entity.toSnapshot();

        assertThat(snapshot.id()).isEqualTo(7);
        assertThat(snapshot.name()).isEqualTo("数据结构");
        assertThat(snapshot.description()).isNull();
        assertThat(snapshot.locked()).isNull();
        assertThat(snapshot.plazaBoardId()).isEqualTo(12);
        assertThat(snapshot.plazaFeatured()).isTrue();
        assertThat(snapshot.plazaFeaturedWeight()).isEqualTo(30);
        assertThat(snapshot.plazaFeaturedAt()).isEqualTo(featuredAt);
        assertThat(snapshot.createdAt()).isEqualTo(createdAt);
    }

    private static Set<String> idFields() {
        return Arrays.stream(SubjectReadEntity.class.getDeclaredFields())
                .filter(field -> field.isAnnotationPresent(Id.class))
                .map(Field::getName)
                .collect(Collectors.toSet());
    }

    private static boolean hasJpaRelationship(Field field) {
        return field.isAnnotationPresent(ManyToOne.class)
                || field.isAnnotationPresent(OneToMany.class)
                || field.isAnnotationPresent(OneToOne.class)
                || field.isAnnotationPresent(ManyToMany.class);
    }

    private record ColumnShape(Class<?> type, boolean nullable) {}
}
