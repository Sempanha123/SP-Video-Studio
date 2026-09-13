import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    implicitHeight: 126
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm
        Text { text: "Accessibility preview"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.sectionTitle; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: "អ្នករាយការណ៍ · ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ · ผู้สื่อข่าว · Phóng viên"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; lineHeightMode: Text.ProportionalHeight; lineHeight: Theme.type.multilingualLineHeight; wrapMode: Text.WordWrap }
        RowLayout {
            StatusBadge { text: "Needs Review"; status: "warning" }
            SecondaryButton { text: "Keyboard focus"; focus: true }
            Item { Layout.fillWidth: true }
        }
    }
}
