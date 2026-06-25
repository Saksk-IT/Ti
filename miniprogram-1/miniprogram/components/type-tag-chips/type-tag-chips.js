"use strict";
Component({
    properties: {
        types: { type: Array, value: [] },
        tags: { type: Array, value: [] },
        selectedType: { type: String, value: 'all' },
        selectedTag: { type: String, value: 'all' },
        showTypes: { type: Boolean, value: true },
        showTags: { type: Boolean, value: true },
        typeLabel: { type: String, value: '' },
        tagLabel: { type: String, value: '' },
        typeSub: { type: String, value: '' },
        tagSub: { type: String, value: '' },
    },
    methods: {
        onTypeTap: function (e) {
            this.triggerEvent('typetap', { type: e.currentTarget.dataset.type });
        },
        onTagTap: function (e) {
            this.triggerEvent('tagtap', { tag: e.currentTarget.dataset.tag });
        },
        onTagDelete: function (e) {
            this.triggerEvent('tagdelete', { tag: e.currentTarget.dataset.tag });
        },
    },
});
