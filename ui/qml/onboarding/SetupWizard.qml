import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

Popup {
    id: root
    parent: Overlay.overlay
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    width: Math.min(920, parent ? parent.width - 40 : 920)
    height: Math.min(720, parent ? parent.height - 40 : 720)
    modal: true; focus: true; closePolicy: Popup.CloseOnEscape
    padding: 0
    signal projectCreateRequested(string title,string workflow,string language,string aspectRatio,int fps)
    signal navigateRequested(string page,string context)

    background: Rectangle { color: Theme.colors.surface; border.color: Theme.colors.borderStrong; radius: Theme.radius.large }

    contentItem: ColumnLayout {
        spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 64; color: Theme.colors.surface; radius: Theme.radius.large
            RowLayout { anchors.fill: parent; anchors.leftMargin: Theme.spacing.lg; anchors.rightMargin: Theme.spacing.lg
                ColumnLayout { Layout.fillWidth: true; spacing: 1
                    Text { text: Onboarding.currentStep === 0 ? "Getting Started" : "Setup"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                    Text { text: Math.min(Onboarding.currentStep + 1, 7) + " of 7"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                }
                SecondaryButton { text: "Skip Setup"; compact: true; visible: Onboarding.currentStep < 6; onClicked: Onboarding.skip() }
                IconButton { iconName: "close"; tooltip: "Close setup and resume later"; onClicked: root.close() }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            Loader {
                id: pageLoader
                width: parent.width
                sourceComponent: [welcomeComponent,languageComponent,workspaceComponent,readinessComponent,modelComponent,projectComponent,completeComponent][Math.max(0,Math.min(6,Onboarding.currentStep))]
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 68; Layout.leftMargin: Theme.spacing.lg; Layout.rightMargin: Theme.spacing.lg
            SecondaryButton { text: "Back"; visible: Onboarding.currentStep > 0 && Onboarding.currentStep < 6; onClicked: Onboarding.back() }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Go to Home"; visible: Onboarding.currentStep >= 5; onClicked: { Onboarding.finish(); root.close() } }
            AppButton { text: Onboarding.currentStep === 0 ? "Get Started" : (Onboarding.currentStep === 6 ? "Done" : "Next"); visible: Onboarding.currentStep !== 4 && Onboarding.currentStep !== 5; onClicked: { if(Onboarding.currentStep===6){Onboarding.finish();root.close()}else Onboarding.next() } }
        }
    }

    Component { id: welcomeComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; WelcomePage { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }
    Component { id: languageComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; LanguageSetup { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }
    Component { id: workspaceComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; WorkspaceSetup { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }
    Component { id: readinessComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; ReadinessSetup { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }
    Component { id: modelComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; ModelSetup { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }
    Component { id: projectComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; FirstProjectSetup { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2; onCreateRequested:function(title,workflow,language,aspectRatio,fps){root.projectCreateRequested(title,workflow,language,aspectRatio,fps)}; onTemplateRequested:{root.close();Onboarding.openTemplates()} } } }
    Component { id: completeComponent; Item { width: pageLoader.width; implicitHeight: child.implicitHeight + Theme.spacing.xl*2; OnboardingComplete { id: child; x: Theme.spacing.xl; y: Theme.spacing.xl; width: parent.width - Theme.spacing.xl*2 } } }

    onOpened: { if(Onboarding.status === "not_started") Onboarding.begin(); forceActiveFocus() }
}
