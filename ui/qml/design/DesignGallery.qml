import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
ScrollView {
    id: root
    clip: true
    ColumnLayout { width: root.availableWidth; spacing: Theme.spacing.xl
        PageHeader { Layout.fillWidth: true; title: "Soft Creator Studio"; description: "Internal component gallery — debug/design QA only." }
        RowLayout { AppButton { text: "Primary" }; AppButton { text: "Secondary"; variant: "secondary" }; AppButton { text: "Quiet"; variant: "quiet" }; AppButton { text: "Delete"; variant: "danger" } }
        RowLayout { AppTextField { placeholderText: "Search projects…"; Layout.preferredWidth: 240 }; SearchField { placeholderText: "Search assets…"; Layout.preferredWidth: 240 } }
        WorkflowStepper { Layout.fillWidth: true; steps: ["Sources","Script","Voice","Visuals","Export"]; currentIndex: 2 }
        RowLayout { SaveStateBadge { state: "Saved" }; SaveStateBadge { state: "Saving..." }; SaveStateBadge { state: "Unsaved" }; SaveStateBadge { state: "Save failed" } }
        Text { text: "សួស្តី ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ  ·  สวัสดี วันนี้เรามีข่าวใหม่  ·  Xin chào, hôm nay chúng ta có tin tức mới."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; lineHeight: Theme.type.multilingualLineHeight }
    }
}
