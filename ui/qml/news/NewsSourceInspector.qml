import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var source: ({})
    property var snapshot: ({})
    signal claimCreated()
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: root.source.title || "Source Inspector"; color: Theme.colors.textPrimary; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }; SecondaryButton { visible: (root.source.id||"")!==""; text: "Open Source"; compact: true; onClicked: root.controller.openSource(root.source.id) } }
        RowLayout { Layout.fillWidth: true; ComboBox { id: category; Layout.preferredWidth: 180; model: ["official","primary_document","reporting","analysis","press_release","manual_note","other"]; currentIndex: Math.max(0, model.indexOf(root.source.category||"other")) }; AppTextField { id: notes; Layout.fillWidth: true; placeholderText: "Editorial notes (not evidence)"; text: root.source.notes || "" }; SecondaryButton { text: "Save Notes"; compact: true; enabled: (root.source.id||"")!==""; onClicked: root.controller.updateSourceDetails(root.source.id, category.currentText, notes.text) } }
        InfoBanner { Layout.fillWidth: true; visible: !!root.source.sourceUpdated; variant: "warning"; text: "Source Updated — existing claims remain linked to the snapshot they used." }
        TextArea { id: body; Layout.fillWidth: true; Layout.fillHeight: true; readOnly: (root.source.type||"") !== "manual"; wrapMode: TextArea.Wrap; selectByMouse: true; text: root.snapshot.contentText || "Select a ready source to inspect extracted text."; color: Theme.colors.textPrimary; background: Rectangle { color: Theme.colors.surface2; radius: Theme.radius.medium; border.color: Theme.colors.border } }
        AppTextField { id: claimText; Layout.fillWidth: true; placeholderText: "Confirm the factual claim from the selected evidence" }
        RowLayout { Layout.fillWidth: true
            SecondaryButton { visible: (root.source.type||"") === "manual"; text: "Save New Snapshot"; enabled: body.text.trim().length > 0; onClicked: root.controller.updateManualSourceText(root.source.id, body.text) }
            SecondaryButton { text: "Use Selection"; enabled: body.selectedText.length > 0; onClicked: claimText.text = body.selectedText }
            Item { Layout.fillWidth: true }
            AppButton { text: "Create Claim"; enabled: root.controller && claimText.text.trim().length > 0 && (root.snapshot.id || "") !== ""; onClicked: { var ev=body.selectedText.length>0?body.selectedText:claimText.text; if (root.controller.createClaim(root.source.id||"", root.snapshot.id||"", ev, claimText.text, body.selectionStart, body.selectionEnd)) { claimText.text=""; root.claimCreated() } } }
        }
    }
}
