import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: root
    property var selected: typeof voiceController !== "undefined" ? voiceController.selectedVoice : ({})
    property string pendingDeleteId: ""
    property int pendingDeleteAssignments: 0
    property string referenceSource: ""
    property string replaceReferenceSource: ""
    signal navigateRequested(string page, string workflow)
    signal toastRequested(string message, string variant)

    function categoryCode(index) {
        return ["all", "news", "story", "documentary", "professional", "my", "favorites"][index]
    }
    function languageCode(index) { return ["all", "en", "km"][index] }
    function sortCode(index) { return ["recommended", "name", "recent", "favorites"][index] }
    function paceCode(index) { return ["slow", "natural", "fast"][index] }
    function energyCode(index) { return ["low", "medium", "high"][index] }
    function toneCode(index) { return ["calm", "neutral", "confident", "energetic"][index] }
    function numberOr(text, fallback) { var value = Number(text); return isNaN(value) ? fallback : value }
    function tagsFrom(text) {
        var parts = text.split(",")
        var result = []
        for (var i = 0; i < parts.length; ++i) if (parts[i].trim().length) result.push(parts[i].trim())
        return result
    }
    function applyReference(config) {
        if (typeof ttsController !== "undefined") ttsController.setReferencePath(config.referenceAudioPath || "")
    }
    function previewSelected() {
        if (typeof voiceController === "undefined" || typeof ttsController === "undefined") return
        var cfg = voiceController.previewRequestAdvanced(
                    previewText.text,
                    root.paceCode(paceBox.currentIndex), root.energyCode(energyBox.currentIndex), root.toneCode(toneBox.currentIndex),
                    ["auto", "cpu", "cuda"][deviceBox.currentIndex],
                    root.numberOr(cfgField.text, 2.0), Math.round(root.numberOr(stepsField.text, 10)), seedField.text)
        if (!cfg.text) return
        if (cfg.cachedPath) {
            if (typeof playbackController !== "undefined") {
                playbackController.setExternalAudio(cfg.cachedPath, (root.selected.name || "Voice") + " preview", cfg.cachedDuration || 0)
                playbackController.play()
            }
            return
        }
        root.applyReference(cfg)
        ttsController.generatePreview(cfg.text, cfg.mode, cfg.description, cfg.device,
                                      cfg.cfgValue, cfg.inferenceTimesteps,
                                      cfg.seed === null || cfg.seed === undefined ? "" : String(cfg.seed), cfg.consentConfirmed)
    }
    function selectedConfig() {
        if (typeof voiceController === "undefined") return ({})
        return voiceController.selectedConfig(
                    root.paceCode(paceBox.currentIndex), root.energyCode(energyBox.currentIndex), root.toneCode(toneBox.currentIndex),
                    ["auto", "cpu", "cuda"][deviceBox.currentIndex],
                    root.numberOr(cfgField.text, 2.0), Math.round(root.numberOr(stepsField.text, 10)), seedField.text)
    }
    function generateSection() {
        if (typeof ttsController === "undefined" || typeof voiceController === "undefined" || !voiceController.currentSectionId) return
        var cfg = root.selectedConfig(); if (!cfg.mode) return
        root.applyReference(cfg)
        ttsController.generateSection(voiceController.currentSectionId, cfg.mode, cfg.description, cfg.device,
                                      cfg.cfgValue, cfg.inferenceTimesteps,
                                      cfg.seed === null || cfg.seed === undefined ? "" : String(cfg.seed), cfg.consentConfirmed)
    }
    function generateFull() {
        if (typeof ttsController === "undefined" || typeof voiceController === "undefined" || !voiceController.currentProjectId) return
        var cfg = root.selectedConfig(); if (!cfg.mode) return
        root.applyReference(cfg)
        ttsController.generateFull(cfg.mode, cfg.description, cfg.device, cfg.cfgValue, cfg.inferenceTimesteps,
                                   cfg.seed === null || cfg.seed === undefined ? "" : String(cfg.seed), cfg.consentConfirmed)
    }

    Component.onCompleted: {
        if (typeof voiceController !== "undefined") voiceController.refresh()
        if (root.selected.id) previewText.text = voiceController.defaultPreviewText
    }

    Connections {
        target: typeof voiceController !== "undefined" ? voiceController : null
        ignoreUnknownSignals: true
        function onSelectionChanged() {
            root.selected = voiceController.selectedVoice
            previewText.text = voiceController.defaultPreviewText
            if (root.selected.settings) {
                var settings = root.selected.settings
                cfgField.text = String(settings.cfg_value === undefined ? 2.0 : settings.cfg_value)
                stepsField.text = String(settings.inference_timesteps === undefined ? 10 : settings.inference_timesteps)
                seedField.text = settings.seed === undefined || settings.seed === null ? "" : String(settings.seed)
            }
        }
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
        function onDeleteBlocked(voiceId, count) {
            root.pendingDeleteId = voiceId; root.pendingDeleteAssignments = count; deleteDialog.open()
        }
    }
    Connections {
        target: typeof ttsController !== "undefined" ? ttsController : null
        ignoreUnknownSignals: true
        function onPreviewReady(path, name, durationMs) {
            if (typeof playbackController !== "undefined") {
                playbackController.setExternalAudio(path, (root.selected.name || name) + " preview", durationMs)
                playbackController.play()
            }
        }
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.md
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Text { text: "Voice Studio"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Browse fictional presets, save your own voice configurations, and generate narration with VoxCPM2."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            SecondaryButton { text: "Designed Voice"; iconName: "plus"; onClicked: { designName.text = ""; designDescription.text = ""; designTags.text = ""; designedDialog.open() } }
            AppButton { text: "Reference Voice"; iconName: "mic"; onClicked: { root.referenceSource = ""; refName.text = ""; refConsent.checked = false; referenceDialog.open() } }
        }

        InfoBanner {
            Layout.fillWidth: true
            visible: typeof voiceController !== "undefined" && !voiceController.modelReady
            title: "VoxCPM2 is required to generate voice previews"
            description: "You can still browse, favorite, create and assign voices. Install VoxCPM2 when you are ready to generate speech."
            actionText: "Open Models"
            onActionClicked: root.navigateRequested("models", "")
        }

        RowLayout {
            Layout.fillWidth: true; spacing: Theme.spacing.sm
            AppTextField { id: searchField; Layout.fillWidth: true; placeholderText: "Search voices, styles or categories…"; onTextChanged: if (typeof voiceController !== "undefined") voiceController.setSearch(text) }
            AppComboBox { id: languageFilter; Layout.preferredWidth: 132; model: ["All Languages", "English", "Khmer"]; onActivated: if (typeof voiceController !== "undefined") voiceController.setLanguageFilter(root.languageCode(currentIndex)) }
            AppComboBox { id: engineFilter; Layout.preferredWidth: 125; model: ["All Engines", "VoxCPM2"]; onActivated: if (typeof voiceController !== "undefined") voiceController.setEngineFilter(currentIndex === 1 ? "voxcpm2" : "all") }
            AppComboBox { id: sortFilter; Layout.preferredWidth: 145; model: ["Recommended", "Name", "Recently Used", "Favorites"]; onActivated: if (typeof voiceController !== "undefined") voiceController.setSort(root.sortCode(currentIndex)) }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: Theme.spacing.xs
            Repeater {
                model: ["All", "News", "Story", "Documentary", "Professional", "My Voices", "Favorites"]
                delegate: SecondaryButton {
                    required property string modelData
                    required property int index
                    text: modelData; compact: true
                    variant: categoryTabs.currentIndex === index ? "secondary" : "ghost"
                    onClicked: { categoryTabs.currentIndex = index; if (typeof voiceController !== "undefined") voiceController.setCategoryFilter(root.categoryCode(index)) }
                }
            }
            Item { id: categoryTabs; property int currentIndex: 0; Layout.fillWidth: true }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: width < 980 ? Qt.Vertical : Qt.Horizontal

            AppCard {
                SplitView.fillWidth: true; SplitView.fillHeight: true
                SplitView.minimumWidth: 540; SplitView.minimumHeight: 330
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.sm
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Voice Library"; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "English + Khmer"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    }
                    GridView {
                        id: voiceGrid
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; cellWidth: Math.max(250, width / Math.max(1, Math.floor(width / 270))); cellHeight: 190
                        model: typeof voiceController !== "undefined" ? voiceController.voices : null
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        delegate: VoiceCard {
                            width: voiceGrid.cellWidth - Theme.spacing.md; height: 176
                            voiceId: model.voiceId; voiceName: model.name; voiceType: model.voiceType
                            category: model.category; languageName: model.languageName; styleTags: model.styleTags
                            engineName: model.engineName; favorite: model.favorite; recommended: model.recommended; isSelected: model.selected
                            onSelectRequested: function(id) { if (typeof voiceController !== "undefined") voiceController.selectVoice(id) }
                            onPreviewRequested: function(id) { if (typeof voiceController !== "undefined") { voiceController.selectVoice(id); root.previewSelected() } }
                            onFavoriteRequested: function(id) { if (typeof voiceController !== "undefined") voiceController.toggleFavorite(id) }
                        }
                    }
                }
            }

            AppCard {
                SplitView.preferredWidth: 390; SplitView.minimumWidth: 340; SplitView.maximumWidth: 500
                SplitView.fillHeight: true; SplitView.minimumHeight: 330
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                    EmptyState {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        visible: !root.selected.id
                        title: "Select a voice"
                        description: "Choose a preset or one of your saved voices to preview and assign."
                        iconName: "mic"
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        visible: !!root.selected.id
                        spacing: Theme.spacing.md
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle { width: 44; height: 44; radius: 22; color: Theme.colors.accentSoft; Icon { anchors.centerIn: parent; width: 20; height: 20; name: "mic" } }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 1
                                Text { Layout.fillWidth: true; text: root.selected.name || "Voice"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                                Text { text: (root.selected.category || "") + " • " + (root.selected.languageName || "") + " • VoxCPM2"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                            }
                            IconButton { iconName: root.selected.favorite ? "heart-filled" : "heart"; tooltip: "Favorite"; onClicked: voiceController.toggleFavorite(root.selected.id) }
                        }
                        Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.selected.description || root.selected.voiceDescription || "Reusable voice configuration."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                        Text { Layout.fillWidth: true; text: root.selected.styleTags ? root.selected.styleTags.slice(0, 3).join("  •  ") : ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }

                        Text { text: "Preview text"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        TextArea {
                            id: previewText
                            Layout.fillWidth: true; Layout.preferredHeight: 82
                            wrapMode: TextEdit.Wrap; maximumLength: 400; selectByMouse: true
                            color: Theme.colors.textPrimary; placeholderText: "Type a short preview…"; placeholderTextColor: Theme.colors.textMuted
                            font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall
                            background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.surface; border.color: previewText.activeFocus ? Theme.colors.focus : Theme.colors.border; border.width: previewText.activeFocus ? 2 : 1 }
                            padding: Theme.spacing.md
                        }

                        RowLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.sm
                            AppComboBox { id: paceBox; Layout.fillWidth: true; model: ["Slow", "Natural", "Fast"] }
                            AppComboBox { id: energyBox; Layout.fillWidth: true; model: ["Low Energy", "Medium", "High Energy"]; currentIndex: 1 }
                            AppComboBox { id: toneBox; Layout.fillWidth: true; model: ["Calm", "Neutral", "Confident", "Energetic"]; currentIndex: 1 }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            AppSwitch { id: advancedSwitch }
                            Text { text: "Advanced"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                            Item { Layout.fillWidth: true }
                            AppComboBox { id: deviceBox; Layout.preferredWidth: 110; model: ["Auto", "CPU", "CUDA"] }
                        }
                        RowLayout {
                            Layout.fillWidth: true; visible: advancedSwitch.checked; spacing: Theme.spacing.sm
                            AppTextField { id: cfgField; Layout.fillWidth: true; text: "2.0"; placeholderText: "CFG" }
                            AppTextField { id: stepsField; Layout.fillWidth: true; text: "10"; placeholderText: "Steps" }
                            AppTextField { id: seedField; Layout.fillWidth: true; placeholderText: "Seed" }
                        }

                        RowLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.sm
                            AppButton { text: (typeof ttsController !== "undefined" && ttsController.busy) ? "Generating…" : "Preview"; iconName: "play"; enabled: typeof voiceController !== "undefined" && voiceController.modelReady && typeof ttsController !== "undefined" && !ttsController.busy; onClicked: root.previewSelected() }
                            SecondaryButton { text: "Use for Project"; visible: typeof voiceController !== "undefined" && voiceController.currentProjectId.length > 0; onClicked: voiceController.useSelectedForProject() }
                            SecondaryButton { text: "Use for Section"; visible: typeof voiceController !== "undefined" && voiceController.currentSectionId.length > 0; onClicked: voiceController.useSelectedForSection() }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: Theme.spacing.sm
                            SecondaryButton { text: "Generate Section"; visible: typeof voiceController !== "undefined" && voiceController.currentSectionId.length > 0; enabled: voiceController.modelReady && !ttsController.busy; onClicked: root.generateSection() }
                            AppButton { text: "Generate Full Narration"; visible: typeof voiceController !== "undefined" && voiceController.currentProjectId.length > 0; enabled: voiceController.modelReady && !ttsController.busy; onClicked: root.generateFull() }
                        }

                        InfoBanner {
                            Layout.fillWidth: true
                            visible: typeof voiceController !== "undefined" && voiceController.currentProjectId.length > 0
                            title: "Project voice: " + ((voiceController.projectVoice.name || "Not selected"))
                            description: voiceController.currentSectionId.length > 0 ? ("Selected section: " + (voiceController.sectionVoice.name || "Use project voice")) : "Select a script section to set a per-section override."
                            actionText: voiceController.currentSectionId.length > 0 && voiceController.sectionVoice.id ? "Use Project Voice" : ""
                            onActionClicked: voiceController.clearSectionOverride()
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: typeof ttsController !== "undefined" && typeof voiceController !== "undefined" && voiceController.currentProjectId.length > 0 && ttsController.generated.length > 0
                            spacing: Theme.spacing.xs
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Narration Takes"; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
                                Text { text: "Recent " + Math.min(5, ttsController.generated.length); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                            }
                            Repeater {
                                model: typeof ttsController !== "undefined" ? ttsController.generated.slice(0, 5) : []
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    radius: Theme.radius.small
                                    color: modelData.active ? Theme.colors.accentSoft : Theme.colors.surfaceRaised
                                    border.color: Theme.colors.border
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: Theme.spacing.xs; spacing: Theme.spacing.xs
                                        ColumnLayout {
                                            Layout.fillWidth: true; spacing: 0
                                            Text { Layout.fillWidth: true; text: modelData.active ? "Current take" : (modelData.current ? "Ready take" : "Out of date"); color: modelData.current ? Theme.colors.textPrimary : Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                                            Text { text: modelData.durationDisplay || "00:00"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 10 }
                                        }
                                        IconButton { iconName: "play"; tooltip: "Play narration"; onClicked: { if (typeof playbackController !== "undefined") { playbackController.setExternalAudio(modelData.filePath, "Narration take", modelData.durationMs || 0); playbackController.play() } } }
                                        SecondaryButton { text: "Set Active"; compact: true; visible: !modelData.active; onClicked: ttsController.setActiveGenerated(modelData.id) }
                                        IconButton { iconName: "trash"; tooltip: "Delete narration take"; onClicked: ttsController.deleteGenerated(modelData.id) }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            Layout.fillWidth: true; visible: root.selected.id && !root.selected.isBuiltin
                            SecondaryButton { text: "Edit"; iconName: "edit"; onClicked: { editName.text=root.selected.name||""; editDescription.text=root.selected.voiceDescription||""; editTags.text=(root.selected.styleTags||[]).join(", "); editDialog.open() } }
                            SecondaryButton { text: "Duplicate"; iconName: "copy"; onClicked: voiceController.duplicateVoice(root.selected.id) }
                            SecondaryButton { text: "Replace Audio"; visible: root.selected.voiceType === "reference"; onClicked: { replaceConsent.checked=false; replaceReferenceDialog.open() } }
                            Item { Layout.fillWidth: true }
                            IconButton { iconName: "trash"; tooltip: "Delete voice"; onClicked: { root.pendingDeleteId=root.selected.id; root.pendingDeleteAssignments=voiceController.assignmentCount(root.selected.id); deleteDialog.open() } }
                        }
                    }
                }
            }
        }
    }

    AppDialog {
        id: designedDialog
        width: 560; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: "Create Designed Voice"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Describe the result in everyday language. You can save now and preview later if the model is not installed."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Layout.fillWidth: true; AppTextField { id: designName; Layout.fillWidth: true; placeholderText: "Voice name" }; AppComboBox { id: designLanguage; Layout.preferredWidth: 130; model: ["English", "Khmer"] } }
            AppComboBox { id: designCategory; Layout.fillWidth: true; model: ["News Anchor", "Storyteller", "Documentary", "Professional", "Friendly", "Educational", "Energetic", "Calm", "Conversational", "Dramatic"] }
            TextArea {
                id: designDescription; Layout.fillWidth: true; Layout.preferredHeight: 120; wrapMode: TextEdit.Wrap; maximumLength: 800
                placeholderText: "Example: Professional technology news narrator, clear articulation, slightly energetic, confident but not dramatic."
                color: Theme.colors.textPrimary; placeholderTextColor: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; padding: Theme.spacing.md
                background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.surface; border.color: designDescription.activeFocus ? Theme.colors.focus : Theme.colors.border }
            }
            AppTextField { id: designTags; Layout.fillWidth: true; placeholderText: "Style tags, comma separated (Warm, Clear, Confident)" }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: designedDialog.close() }; AppButton { text: "Save Voice"; onClicked: { var id=voiceController.createDesigned(designName.text, designLanguage.currentIndex===1?"km":"en", designCategory.currentText, designDescription.text, root.tagsFrom(designTags.text)); if(id) designedDialog.close() } } }
        }
    }

    AppDialog {
        id: referenceDialog
        width: 560; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: "Add Reference Voice"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Use only a recording you own or have permission to use. Reference recordings stay local in your Voice Library."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Layout.fillWidth: true; AppTextField { id: refName; Layout.fillWidth: true; placeholderText: "Voice name" }; AppComboBox { id: refLanguage; Layout.preferredWidth: 130; model: ["English", "Khmer"] } }
            AppComboBox { id: refCategory; Layout.fillWidth: true; model: ["Professional", "News Anchor", "Storyteller", "Documentary", "Friendly", "Conversational"] }
            RowLayout { Layout.fillWidth: true; AppTextField { Layout.fillWidth: true; readOnly: true; text: root.referenceSource; placeholderText: "Choose authorized audio" }; SecondaryButton { text: "Choose…"; onClicked: referenceFile.open() } }
            RowLayout { Layout.fillWidth: true; AppSwitch { id: refConsent }; Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "I have permission to use this voice recording."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: referenceDialog.close() }; AppButton { text: "Save Voice"; enabled: refConsent.checked && root.referenceSource.length>0; onClicked: { var id=voiceController.createReference(refName.text, refLanguage.currentIndex===1?"km":"en", refCategory.currentText, root.referenceSource, refConsent.checked); if(id) referenceDialog.close() } } }
        }
    }
    FileDialog { id: referenceFile; title: "Choose Authorized Voice Recording"; fileMode: FileDialog.OpenFile; nameFilters: ["Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac)", "All Files (*.*)"]; onAccepted: root.referenceSource = selectedFile }

    AppDialog {
        id: editDialog
        width: 540; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: "Edit Voice"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            AppTextField { id: editName; Layout.fillWidth: true; placeholderText: "Voice name" }
            AppTextField { id: editDescription; Layout.fillWidth: true; visible: root.selected.voiceType === "designed"; placeholderText: "Voice description" }
            AppTextField { id: editTags; Layout.fillWidth: true; placeholderText: "Style tags, comma separated" }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: editDialog.close() }; AppButton { text: "Save"; onClicked: { if(voiceController.editVoice(root.selected.id, editName.text, root.selected.language, root.selected.category, editDescription.text, root.tagsFrom(editTags.text), root.selected.notes||"")) editDialog.close() } } }
        }
    }

    AppDialog {
        id: deleteDialog
        width: 500; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.lg
            Text { text: "Delete this voice?"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.pendingDeleteAssignments > 0 ? ("This voice is currently used by " + root.pendingDeleteAssignments + " project/section assignment(s). Delete will clear those assignments, but existing generated audio stays untouched.") : "This removes the saved voice definition. Existing generated audio stays untouched."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: deleteDialog.close() }; AppButton { text: root.pendingDeleteAssignments > 0 ? "Delete and Clear Assignments" : "Delete"; variant: "danger"; onClicked: { if(voiceController.deleteVoice(root.pendingDeleteId, root.pendingDeleteAssignments>0)) deleteDialog.close() } } }
        }
    }

    AppDialog {
        id: replaceReferenceDialog
        width: 500; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: "Replace Reference Recording"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            RowLayout { Layout.fillWidth: true; AppTextField { Layout.fillWidth: true; readOnly: true; text: root.replaceReferenceSource; placeholderText: "Choose new recording" }; SecondaryButton { text: "Choose…"; onClicked: replaceReferenceFile.open() } }
            RowLayout { Layout.fillWidth: true; AppSwitch { id: replaceConsent }; Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "I have permission to use this voice recording."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall } }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; SecondaryButton { text: "Cancel"; onClicked: replaceReferenceDialog.close() }; AppButton { text: "Replace"; enabled: replaceConsent.checked && root.replaceReferenceSource.length>0; onClicked: { if(voiceController.replaceReference(root.selected.id, root.replaceReferenceSource, replaceConsent.checked)) replaceReferenceDialog.close() } } }
        }
    }
    FileDialog { id: replaceReferenceFile; title: "Choose New Reference Recording"; fileMode: FileDialog.OpenFile; nameFilters: ["Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.aac)", "All Files (*.*)"]; onAccepted: root.replaceReferenceSource = selectedFile }
}
