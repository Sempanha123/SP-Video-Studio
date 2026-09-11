import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
AppCard {
    id: root
    property var controller
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        SectionHeader { title: "Project News Theme"; subtitle: "One consistent visual language. Existing manual overlays stay untouched." }
        Flow {
            Layout.fillWidth: true; spacing: Theme.spacing.xs
            Repeater { model: root.controller ? root.controller.builtinThemes : []
                AppButton { text: modelData.name; compact: true; variant: root.controller && root.controller.theme.presetId===modelData.id ? "secondary" : "ghost"; onClicked: root.controller.applyTheme(modelData.id) }
            }
        }
        GridLayout { Layout.fillWidth: true; columns: 2; columnSpacing: Theme.spacing.sm; rowSpacing: Theme.spacing.xs
            Text { text: "Primary"; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
            AppTextField { id: primary; Layout.fillWidth: true; text: root.controller ? (root.controller.theme.primaryColor || "#18212B") : "#18212B" }
            Text { text: "Accent"; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
            AppTextField { id: accent; Layout.fillWidth: true; text: root.controller ? (root.controller.theme.accentColor || "#D8A84E") : "#D8A84E" }
            Text { text: "Heading font"; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
            AppTextField { id: heading; Layout.fillWidth: true; text: root.controller ? (root.controller.theme.fontHeading || "Noto Sans Khmer") : "Noto Sans Khmer" }
            Text { text: "Body font"; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
            AppTextField { id: body; Layout.fillWidth: true; text: root.controller ? (root.controller.theme.fontBody || "Noto Sans Khmer") : "Noto Sans Khmer" }
        }
        SecondaryButton { text: "Apply custom theme"; compact: true; onClicked: if(root.controller) root.controller.customizeTheme(primary.text,accent.text,heading.text,body.text) }
    }
}
